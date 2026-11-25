"""Confirmed recovery addresses are separate from external login identities."""
import hashlib
import logging
import uuid
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.mail import EmailMessage
from django.db import connection, transaction, IntegrityError
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from login.models import AccountEmailDelivery, PasswordResetDelivery, User
from login.password_reset import public_origin, allow_request
from login.security import security_changed
from login.security_views import require_recent

logger = logging.getLogger(__name__)
SALT = 'myfinance-email-confirmation'


class EmailChangeForm(forms.Form):
    email = forms.EmailField(
        label='E-mail de recuperação',
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'}),
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip().casefold()


@never_cache
@require_recent
def request_change(request):
    form = EmailChangeForm(
        request.POST if request.method == 'POST' else None,
        initial={'email': request.GET.get('email', request.user.email)},
    )
    if request.method == 'POST' and form.is_valid():
        target = form.cleaned_data['email']
        if User.objects.filter(email__iexact=target).exclude(pk=request.user.pk).exists():
            form.add_error('email', 'Não foi possível usar este endereço. Informe outro e-mail.')
        elif allow_request(request, str(request.user.pk), purpose='email-confirmation'):
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=request.user.pk)
                user.pending_email = target
                user.email_confirmation_nonce = uuid.uuid4()
                user.email_requested_at = timezone.now()
                user.save(update_fields=['pending_email', 'email_confirmation_nonce', 'email_requested_at'])
                AccountEmailDelivery.objects.filter(user=user, kind='confirm').delete()
                AccountEmailDelivery.objects.create(
                    user=user,
                    kind='confirm',
                    nonce=user.email_confirmation_nonce,
                    credential_stamp=user.get_session_auth_hash(),
                )
            messages.success(
                request,
                'Enviamos a solicitação para processamento. Confirme o novo endereço pelo link recebido; seu e-mail atual continua valendo até a confirmação.',
            )
            return redirect('account_security')
        else:
            form.add_error(None, 'Aguarde alguns minutos antes de solicitar outra confirmação.')
    return render(
        request,
        'user/security/form.html',
        {'form': form, 'security_title': 'Confirmar ou alterar e-mail de recuperação'},
    )


@never_cache
@require_POST
@login_required
def cancel_change(request):
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.pk)
        user.pending_email = ''
        user.email_confirmation_nonce = uuid.uuid4()
        user.email_requested_at = None
        user.save(update_fields=['pending_email', 'email_confirmation_nonce', 'email_requested_at'])
        AccountEmailDelivery.objects.filter(user=user, kind='confirm').delete()
    messages.success(request, 'Solicitação de e-mail cancelada.')
    return redirect('account_security')


def confirmation_payload(user):
    return {
        'uid': user.pk,
        'nonce': str(user.email_confirmation_nonce),
        'target': hashlib.sha256(user.pending_email.encode()).hexdigest(),
        'stamp': user.get_session_auth_hash(),
    }


def valid_confirmation(user, token):
    try:
        payload = signing.loads(token, salt=SALT, max_age=86400)
        return (
            user.is_active
            and bool(user.pending_email)
            and user.email_requested_at is not None
            and timezone.now() - user.email_requested_at < timedelta(days=1)
            and payload == confirmation_payload(user)
        )
    except (signing.BadSignature, ValueError, TypeError):
        return False


@never_cache
@require_recent
def confirm_change(request, token):
    if not valid_confirmation(request.user, token):
        return render(request, 'user/security/email_confirm.html', {'validlink': False})
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=request.user.pk)
                if not valid_confirmation(user, token):
                    return render(request, 'user/security/email_confirm.html', {'validlink': False})
                if User.objects.filter(email__iexact=user.pending_email).exclude(pk=user.pk).exists():
                    messages.error(request, 'Este endereço não está disponível. Solicite uma nova confirmação.')
                    return redirect('account_security')
                old, verified = user.email, bool(user.email_verified_at)
                changed = old != user.pending_email
                user.email = user.pending_email
                user.pending_email = ''
                user.email_verified_at = timezone.now()
                user.email_confirmation_nonce = uuid.uuid4()
                user.email_requested_at = None
                user.save(
                    update_fields=[
                        'email',
                        'pending_email',
                        'email_verified_at',
                        'email_confirmation_nonce',
                        'email_requested_at',
                    ]
                )
                AccountEmailDelivery.objects.filter(user=user, kind='confirm').delete()
                if changed:
                    PasswordResetDelivery.objects.filter(user=user).delete()
                    security_changed(user, request, event='recovery_email_changed')
                    if verified:
                        AccountEmailDelivery.objects.create(user=user, kind='notice', recipient=old)
        except IntegrityError:
            messages.error(request, 'Este endereço não está disponível. Solicite uma nova confirmação.')
            return redirect('account_security')
        messages.success(request, 'E-mail de recuperação confirmado.')
        return redirect('account_security')
    return render(
        request, 'user/security/email_confirm.html', {'validlink': True, 'target_email': request.user.pending_email}
    )


def process_account_email():
    now = timezone.now()
    AccountEmailDelivery.objects.filter(created_at__lte=now - timedelta(days=1)).delete()
    with transaction.atomic():
        items = (
            AccountEmailDelivery.objects.filter(available_at__lte=now)
            .filter(
                Q(locked_until__isnull=True) | Q(locked_until__lte=now),
            )
            .order_by('pk')
        )
        options = {'skip_locked': True} if connection.features.has_select_for_update_skip_locked else {}
        item = items.select_for_update(**options).first()
        if item is None:
            return False
        item.claim = uuid.uuid4()
        item.locked_until = now + timedelta(minutes=5)
        item.attempts += 1
        item.save(update_fields=['claim', 'locked_until', 'attempts'])
    owned = AccountEmailDelivery.objects.filter(pk=item.pk, claim=item.claim)
    user = User.objects.filter(pk=item.user_id).first()
    if not user or not user.is_active or item.attempts > 3:
        owned.delete()
        return True
    try:
        if item.kind == 'confirm':
            if (
                not user.pending_email
                or user.email_confirmation_nonce != item.nonce
                or not constant_time_compare(user.get_session_auth_hash(), item.credential_stamp)
            ):
                owned.delete()
                return True
            token = signing.dumps(confirmation_payload(user), salt=SALT, compress=True)
            url = public_origin() + reverse('confirm_account_email', kwargs={'token': token})
            recipient = user.pending_email
            subject = 'MyFinance — Confirme seu e-mail de recuperação'
            body = f'Confirme o endereço de recuperação do MyFinance:\n\n{url}\n\nEntre na mesma conta para concluir. O link expira em 24 horas. Se não solicitou, ignore esta mensagem.'
        elif item.kind == 'notice':
            recipient = item.recipient
            subject = 'MyFinance — E-mail de recuperação alterado'
            body = 'O e-mail de recuperação da sua conta MyFinance foi alterado após confirmação do novo endereço. Se não reconhece esta ação, entre em contato com o administrador.'
        else:
            owned.delete()
            return True
        if EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient]).send() != 1:
            raise RuntimeError('Delivery not accepted')
    except Exception:
        logger.error('account_email_delivery_failed item=%s attempt=%s', item.pk, item.attempts)
        if item.attempts >= 3:
            owned.delete()
        else:
            owned.update(claim=None, locked_until=None, available_at=now + timedelta(seconds=60 * 2**item.attempts))
    else:
        owned.delete()
    return True
