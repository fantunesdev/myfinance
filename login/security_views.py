import secrets
import time
from functools import wraps
from urllib.parse import quote

import segno
from django import forms
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from login.models import RecoveryCode, TwoFactorDevice, User
from login import security


class CodeForm(forms.Form):
    code = forms.CharField(
        label='Código do autenticador ou de recuperação',
        max_length=64,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'one-time-code'}),
    )


class ReauthenticationForm(CodeForm):
    password = forms.CharField(
        label='Senha atual',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'}),
    )


def require_recent(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not security.recent(request):
            match = request.resolver_match
            request.session['security_return'] = (
                reverse('account_security')
                if match and match.url_name == 'two_factor_manage'
                else request.get_full_path()
            )
            return redirect('security_reauthenticate')
        return view(request, *args, **kwargs)

    return wrapped


def safe_destination(request, value):
    return (
        value
        if value
        and value.startswith('/')
        and not value.startswith('//')
        and url_has_allowed_host_and_scheme(
            value,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
        else '/'
    )


@never_cache
@sensitive_post_parameters('code')
def challenge(request):
    pending = request.session.get('pending_mfa', {})
    user = User.objects.filter(pk=pending.get('user')).first() if pending.get('user') else None
    if (
        not user
        or not user.is_active
        or not user.two_factor_enabled
        or not 0 <= time.time() - pending.get('at', 0) <= 300
        or not constant_time_compare(user.get_session_auth_hash(), pending.get('stamp', ''))
    ):
        request.session.pop('pending_mfa', None)
        messages.error(request, 'A confirmação expirou. Entre novamente.')
        return redirect('login_user')
    form = CodeForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        if security.verify_factor(user, form.cleaned_data['code'], ip=request.META.get('REMOTE_ADDR', '')):
            # Recheck the identity stamp after verifying to reject concurrent security changes.
            user.refresh_from_db()
            if constant_time_compare(user.get_session_auth_hash(), pending['stamp']):
                request.session.pop('pending_mfa', None)
                security.finish_login(request, user, pending['backend'], google=pending.get('google', False))
                return redirect(safe_destination(request, pending.get('destination')))
        form.add_error(
            'code', 'Código inválido, já utilizado ou temporariamente bloqueado. Aguarde antes de tentar novamente.'
        )
    return render(request, 'user/security/form.html', {'form': form, 'security_title': 'Confirmar segundo fator'})


@never_cache
@login_required
@sensitive_post_parameters('password', 'code')
def reauthenticate(request):
    form = ReauthenticationForm(request.POST if request.method == 'POST' else None)
    if not request.user.two_factor_enabled:
        form.fields['code'].required = False
        form.fields['code'].widget = forms.HiddenInput()
    if not request.user.has_usable_password():
        form.fields['password'].widget = forms.HiddenInput()
    if request.method == 'POST' and form.is_valid():
        from login.password_reset import allow_request

        allowed = allow_request(request, str(request.user.pk), purpose='security-reauth')
        google = request.session.get('google_reauthenticated', {})
        primary = (
            request.user.check_password(form.cleaned_data.get('password', ''))
            if request.user.has_usable_password()
            else (google.get('user') == str(request.user.pk) and 0 <= time.time() - google.get('at', 0) <= 300)
        )
        # A social-only account can refresh its OTP before starting Google reauthentication.
        if allowed and request.user.two_factor_enabled:
            factor = security.verify_factor(
                request.user, form.cleaned_data['code'], ip=request.META.get('REMOTE_ADDR', '')
            )
        else:
            factor = not request.user.two_factor_enabled
        if allowed and factor:
            request.session['mfa_version'] = request.user.security_version
            request.session['mfa_verified_at'] = time.time()
            if primary:
                request.session['reauthenticated_at'] = time.time()
                return redirect(safe_destination(request, request.session.pop('security_return', '/usuarios/perfil/')))
            if not request.user.has_usable_password():
                messages.info(request, 'Segundo fator confirmado. Confirme agora sua conta Google.')
                return redirect('account_security')
        form.add_error(
            None, 'Não foi possível confirmar sua identidade. Verifique os dados ou aguarde para tentar novamente.'
        )
    return render(
        request,
        'user/security/form.html',
        {
            'form': form,
            'security_title': 'Confirmar identidade',
            'show_google': not request.user.has_usable_password(),
            'google_only': not request.user.has_usable_password() and not request.user.two_factor_enabled,
        },
    )


@never_cache
@login_required
def overview(request):
    return render(
        request,
        'user/security/overview.html',
        {
            'recovery_codes_remaining': RecoveryCode.objects.filter(user=request.user).count(),
            'linked_accounts': request.user.social_auth.filter(provider='google-oauth2'),
        },
    )


@never_cache
@require_recent
@sensitive_post_parameters('code')
def setup(request):
    if not request.user.email_verified_at:
        messages.error(request, 'Confirme seu e-mail de recuperação antes de ativar ou substituir o autenticador.')
        return redirect('account_security')
    try:
        security.cipher()
    except Exception:
        messages.error(
            request, 'O autenticador está indisponível. O administrador precisa configurar a chave de proteção.'
        )
        return redirect('account_security')
    if request.method == 'POST' and request.POST.get('action') == 'start':
        with transaction.atomic():
            current = User.objects.select_for_update().get(pk=request.user.pk)
            device, _ = TwoFactorDevice.objects.get_or_create(user=current)
            device.pending_secret = security.cipher().encrypt(security.new_secret()).decode()
            device.pending_created_at = timezone.now()
            device.save(update_fields=['pending_secret', 'pending_created_at'])
        return redirect('two_factor_setup')
    device = TwoFactorDevice.objects.filter(user=request.user).first()
    form = CodeForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            current = User.objects.select_for_update().get(pk=request.user.pk)
            if security.verify_factor(
                current, form.cleaned_data['code'], enrollment=True, ip=request.META.get('REMOTE_ADDR', '')
            ):
                device = TwoFactorDevice.objects.get(user=current)
                device.encrypted_secret = device.pending_secret
                device.pending_secret = ''
                device.pending_created_at = None
                device.confirmed = True
                device.save(update_fields=['encrypted_secret', 'pending_secret', 'pending_created_at', 'confirmed'])
                current.two_factor_enabled = True
                current.save(update_fields=['two_factor_enabled'])
                codes = security.generate_recovery_codes(current)
                security.security_changed(current, request, event='two_factor_enabled')
                return render(request, 'user/security/codes.html', {'codes': codes})
        form.add_error('code', 'Código inválido, expirado ou bloqueado. Aguarde antes de tentar novamente.')
    form.fields['code'].label = 'Código do novo autenticador'
    context = {'form': form, 'security_title': 'Configurar autenticador'}
    if (
        device
        and device.pending_secret
        and device.pending_created_at
        and timezone.now() - device.pending_created_at < timezone.timedelta(minutes=10)
    ):
        secret = security.cipher().decrypt(device.pending_secret.encode())
        text = security.key_text(secret)
        uri = f'otpauth://totp/{quote("MyFinance:"+request.user.username, safe="")}?secret={text}&issuer=MyFinance&algorithm=SHA1&digits=6&period=30'
        context.update({'secret': text, 'qr': segno.make(uri, micro=False).svg_data_uri(scale=5)})
    return render(request, 'user/security/setup.html', context)


@never_cache
@require_POST
@require_recent
@sensitive_post_parameters('code')
def manage_factor(request):
    action = request.POST.get('action')
    if action not in ('disable', 'codes'):
        return HttpResponseBadRequest('Ação inválida.')
    with transaction.atomic():
        current = User.objects.select_for_update().get(pk=request.user.pk)
        if not security.verify_factor(current, request.POST.get('code', ''), ip=request.META.get('REMOTE_ADDR', '')):
            messages.error(request, 'Confirme com um código válido do autenticador ou de recuperação.')
            return redirect('account_security')
        if action == 'disable':
            current.two_factor_enabled = False
            current.save(update_fields=['two_factor_enabled'])
            TwoFactorDevice.objects.filter(user=current).delete()
            RecoveryCode.objects.filter(user=current).delete()
            security.security_changed(current, request, event='two_factor_disabled')
            messages.success(request, 'Autenticação em duas etapas desativada.')
        else:
            codes = security.generate_recovery_codes(current)
            security.security_changed(current, request, event='recovery_codes_regenerated')
            return render(request, 'user/security/codes.html', {'codes': codes})
    return redirect('account_security')
