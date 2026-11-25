"""Shared identity, second-factor and session policy."""
import base64
import hashlib
import secrets
import time
from datetime import timedelta

from cryptography.fernet import Fernet
from django.apps import apps
from django.conf import settings
from django.contrib.auth import login, update_session_auth_hash
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django_otp.oath import TOTP

from login.models import RecoveryCode, TwoFactorDevice, User


def cipher():
    key = getattr(settings, 'TWO_FACTOR_ENCRYPTION_KEY', '')
    if not key:
        raise ImproperlyConfigured('Configure TWO_FACTOR_ENCRYPTION_KEY antes de ativar 2FA.')
    return Fernet(key.encode())


def new_secret():
    return secrets.token_bytes(20)


def secret_for(device, enrollment=False):
    return cipher().decrypt((device.pending_secret if enrollment else device.encrypted_secret).encode())


def key_text(secret):
    return base64.b32encode(secret).decode().rstrip('=')


def code_digest(value):
    return hashlib.sha256(value.replace('-', '').replace(' ', '').lower().encode()).hexdigest()


def generate_recovery_codes(user):
    RecoveryCode.objects.filter(user=user).delete()
    codes = ['-'.join([raw[i : i + 8] for i in range(0, 32, 8)]) for raw in (secrets.token_hex(16) for _ in range(10))]
    RecoveryCode.objects.bulk_create([RecoveryCode(user=user, digest=code_digest(code)) for code in codes])
    return codes


def attempt_allowed(user, ip=''):
    try:
        key = 'mfa-ip:' + salted_hmac('mfa-ip', ip, algorithm='sha256').hexdigest()
        count = 1 if cache.add(key, 1, 300) else cache.incr(key)
        return count <= 30
    except Exception:
        return False


def verify_factor(user, value, *, ip='', enrollment=False):
    if not value or not attempt_allowed(user, ip):
        return False
    with transaction.atomic():
        current = User.objects.select_for_update().get(pk=user.pk)
        device = TwoFactorDevice.objects.select_for_update().filter(user=current).first()
        now = timezone.now()
        if not current.is_active or not device or (not enrollment and not current.two_factor_enabled):
            return False
        if not enrollment and not device.confirmed:
            return False
        if enrollment and (not device.pending_created_at or now - device.pending_created_at > timedelta(minutes=10)):
            return False
        if device.locked_until and device.locked_until > now:
            return False
        accepted = False
        raw = value.strip()
        if raw.isascii() and raw.isdigit() and len(raw) == 6:
            try:
                totp = TOTP(secret_for(device, enrollment))
                accepted = totp.verify(int(raw), tolerance=1, min_t=0 if enrollment else device.last_t + 1)
            except Exception:
                accepted = False
            if accepted:
                device.last_t = totp.t()
        elif not enrollment:
            digest = code_digest(raw)
            for code in RecoveryCode.objects.filter(user=current):
                if constant_time_compare(code.digest, digest):
                    code.delete()
                    accepted = True
                    break
        if accepted:
            device.failures = 0
            device.locked_until = None
        else:
            device.failures = min(20, device.failures + 1)
            device.locked_until = now + timedelta(seconds=min(300, 2**device.failures))
        device.save(update_fields=['last_t', 'failures', 'locked_until'])
        return accepted


def mark_session(request, user, *, google=False):
    request.session['mfa_version'] = user.security_version
    request.session['mfa_verified_at'] = time.time()
    request.session['reauthenticated_at'] = time.time()
    request.session['inactivity_browser_id'] = secrets.token_urlsafe(24)
    if google:
        request.session['google_reauthenticated'] = {'user': str(user.pk), 'at': time.time()}


def finish_login(request, user, backend, *, google=False):
    request.session.pop('pending_mfa', None)
    login(request, user, backend=backend)
    mark_session(request, user, google=google)


def begin_login(request, user, backend, *, google=False, destination='/'):
    if not user.two_factor_enabled:
        finish_login(request, user, backend, google=google)
        return False
    if request.user.is_authenticated:
        from django.contrib.auth import logout

        logout(request)
    request.session.cycle_key()
    request.session['pending_mfa'] = {
        'user': str(user.pk),
        'backend': backend,
        'stamp': user.get_session_auth_hash(),
        'at': time.time(),
        'google': google,
        'destination': destination,
    }
    return True


def recent(request):
    return 0 <= time.time() - request.session.get('reauthenticated_at', 0) <= 300 and (
        not request.user.two_factor_enabled
        or (
            request.session.get('mfa_version') == request.user.security_version
            and 0 <= time.time() - request.session.get('mfa_verified_at', 0) <= 300
        )
    )


def otp_recent(request):
    return request.session.get('mfa_version') == request.user.security_version and (
        0 <= time.time() - request.session.get('mfa_verified_at', 0) <= 300
    )


def security_changed(user, request=None, event='security_changed', reason=''):
    """Call under the user lock. Invalidate prior sessions and human API grants."""
    from login.models import SecurityAuditEvent

    SecurityAuditEvent.objects.create(user=user, kind=event, reason=reason[:240])
    user.security_version += 1
    user.save(update_fields=['security_version'])
    if apps.is_installed('oauth2_provider'):
        from oauth2_provider.models import AccessToken, RefreshToken, Grant

        RefreshToken.objects.filter(user=user).delete()
        AccessToken.objects.filter(user=user).delete()
        Grant.objects.filter(user=user).delete()
    if request is not None:
        update_session_auth_hash(request, user)
        mark_session(request, user)
    # Connections also recheck their session hash before sending data.
    def notify():
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            layer = get_channel_layer()
            if layer:
                async_to_sync(layer.group_send)(f'user_updates_{user.pk}', {'type': 'security_changed'})
        except Exception:
            pass

    transaction.on_commit(notify)


def verified_websocket_session(scope):
    original = scope.get('user')
    session = scope.get('session')
    if not original or not original.is_authenticated or session is None:
        return False
    current = User.objects.filter(pk=original.pk, is_active=True).first()
    return bool(
        current
        and str(session.get('_auth_user_id')) == str(current.pk)
        and constant_time_compare(session.get('_auth_user_hash', ''), current.get_session_auth_hash())
        and (not current.two_factor_enabled or session.get('mfa_version') == current.security_version)
    )
