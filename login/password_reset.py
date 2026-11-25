"""Password recovery with native tokens and a persistent, short-lived outbox."""
import logging
import uuid
from datetime import timedelta
from urllib.parse import urlsplit

from django import forms
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import INTERNAL_RESET_SESSION_TOKEN
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.db import connection, transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from login.models import PasswordResetDelivery, User

logger = logging.getLogger(__name__)


def fingerprint(user):
    return salted_hmac(
        'password-reset-outbox',
        f'{user.pk}:{user.password}:{user.email}:{user.last_login}',
        algorithm='sha256',
    ).hexdigest()


def public_origin():
    value = getattr(settings, 'PUBLIC_BASE_URL', '').rstrip('/')
    parsed = urlsplit(value)
    if (
        parsed.scheme not in ('http', 'https')
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
        or (not settings.DEBUG and parsed.scheme != 'https')
    ):
        raise ImproperlyConfigured('Configure PUBLIC_BASE_URL com a origem pública HTTPS da aplicação.')
    return value


def allow_request(request, email):
    """Atomic counters; never trust caller-supplied forwarding headers."""
    window = getattr(settings, 'PASSWORD_RESET_RATE_WINDOW', 900)
    limits = (
        ('ip', request.META.get('REMOTE_ADDR', ''), getattr(settings, 'PASSWORD_RESET_IP_LIMIT', 30)),
        ('email', email.strip().casefold(), getattr(settings, 'PASSWORD_RESET_EMAIL_LIMIT', 3)),
    )
    allowed = True
    try:
        for kind, value, limit in limits:
            digest = salted_hmac('password-reset-rate', value, algorithm='sha256').hexdigest()
            key = f'password-reset:{kind}:{digest}'
            if cache.add(key, 1, timeout=window):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:  # The window expired between add and incr.
                    count = 1 if cache.add(key, 1, timeout=window) else cache.incr(key)
            allowed = allowed and count <= limit
    except Exception:
        # A cache outage must not enable unlimited email delivery.
        logger.error('password_reset_rate_limit_unavailable')
        return False
    return allowed


class RecoveryRequestForm(PasswordResetForm):
    email = forms.EmailField(
        label='E-mail cadastrado',
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'autocomplete': 'email',
            }
        ),
    )


class RecoveryPrivacyMixin:
    def dispatch(self, *args, **kwargs):
        response = super().dispatch(*args, **kwargs)
        response['Referrer-Policy'] = 'strict-origin'
        response['Cache-Control'] = 'no-store'
        return response


class RecoverySetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control', 'autocomplete': 'new-password'})


@method_decorator(never_cache, name='dispatch')
@method_decorator(sensitive_post_parameters('email'), name='dispatch')
class RecoveryRequestView(RecoveryPrivacyMixin, auth_views.PasswordResetView):
    template_name = 'user/recovery/request.html'
    form_class = RecoveryRequestForm
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        if allow_request(self.request, form.cleaned_data['email']):
            try:
                users = list(form.get_users(form.cleaned_data['email']))
                # Ambiguous legacy addresses must not select an arbitrary account.
                user = users[0] if len(users) == 1 else None
                PasswordResetDelivery.objects.create(
                    user=user,
                    credential_fingerprint=fingerprint(user) if user else '',
                )
            except Exception:
                logger.error('password_reset_enqueue_failed')
        return redirect(self.success_url)


class RecoveryConfirmView(RecoveryPrivacyMixin, auth_views.PasswordResetConfirmView):
    template_name = 'user/recovery/confirm.html'
    form_class = RecoverySetPasswordForm
    success_url = reverse_lazy('password_reset_complete')
    post_reset_login = False

    def get_user(self, uidb64):
        user = super().get_user(uidb64)
        return user if user and user.is_active and user.has_usable_password() else None

    def form_valid(self, form):
        # Recheck under a user lock so two simultaneous submissions cannot reuse a token.
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=self.user.pk)
            token = self.request.session.get(INTERNAL_RESET_SESSION_TOKEN)
            if (
                not user.is_active
                or not user.has_usable_password()
                or not self.token_generator.check_token(user, token)
            ):
                self.validlink = False
                return self.render_to_response(self.get_context_data())
            form.user = user
            result = super().form_valid(form)
            PasswordResetDelivery.objects.filter(user=user).delete()
            self.request.session.pop('google_reauthenticated', None)
        return result


class RecoveryDoneView(RecoveryPrivacyMixin, auth_views.PasswordResetDoneView):
    template_name = 'user/recovery/done.html'


class RecoveryCompleteView(RecoveryPrivacyMixin, auth_views.PasswordResetCompleteView):
    template_name = 'user/recovery/complete.html'


def process_delivery():
    """Claim one item. Leases recover after worker crashes; retries are bounded."""
    now = timezone.now()
    timeout = settings.PASSWORD_RESET_TIMEOUT
    PasswordResetDelivery.objects.filter(created_at__lte=now - timedelta(seconds=timeout)).delete()
    with transaction.atomic():
        items = (
            PasswordResetDelivery.objects.filter(available_at__lte=now)
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
    owned = PasswordResetDelivery.objects.filter(pk=item.pk, claim=item.claim)
    if item.attempts > 3:
        owned.delete()
        return True
    user = User.objects.filter(pk=item.user_id).first() if item.user_id else None
    if (
        not user
        or not user.is_active
        or not user.has_usable_password()
        or not constant_time_compare(fingerprint(user), item.credential_fingerprint)
    ):
        owned.delete()
        return True
    try:
        origin = public_origin()
        path = reverse(
            'password_reset_confirm',
            kwargs={
                'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            },
        )
        body = render_to_string(
            'user/recovery/email.txt',
            {
                'reset_url': origin + path,
                'minutes': max(1, timeout // 60),
                'username': user.username,
            },
        )
        message = EmailMultiAlternatives(
            'MyFinance — Recuperação de senha', body, settings.DEFAULT_FROM_EMAIL, [user.email]
        )
        if message.send(fail_silently=False) != 1:
            raise RuntimeError('Delivery not accepted')
    except Exception:
        # No exception details: request bodies and provider responses can contain secrets.
        logger.error('password_reset_delivery_failed item=%s attempt=%s', item.pk, item.attempts)
        if item.attempts >= 3:
            owned.delete()
        else:
            owned.update(claim=None, locked_until=None, available_at=now + timedelta(seconds=60 * 2**item.attempts))
    else:
        owned.delete()
    return True
