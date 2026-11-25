import hashlib
import re
import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.http import HttpResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import include, path
from django.utils import timezone
from django_otp.oath import TOTP
from rest_framework_simplejwt.tokens import RefreshToken
from social_django.models import UserSocialAuth

from login import security, views, social_views
from login.account_email import process_account_email
from login.admin_site import SecurityAdminSite
from login.api_auth import SecureTokenView, SecureRefreshView, SecureJWTAuthentication
from login.forms.user_forms import ProfileForm, UserForm
from login.models import User, Profile, TwoFactorDevice, RecoveryCode, AccountEmailDelivery, SecurityAuditEvent
from login.pipeline import provision_user

urlpatterns = [
    path('usuarios/seguranca/', include('login.security_urls')),
    path('usuarios/senha/', include('login.recovery_urls')),
    path('auth/', include('login.social_urls')),
    path('login/', views.login_user, name='login_user'),
    path('usuarios/perfil/', lambda request: HttpResponse('profile'), name='get_profile'),
    path('private/', lambda request: HttpResponse('private')),
    path('api/token/', SecureTokenView.as_view()),
    path('api/token/refresh/', SecureRefreshView.as_view()),
]
pytestmark = pytest.mark.django_db
KEY = Fernet.generate_key().decode()
BASE = '/usuarios/seguranca/'


@pytest.fixture(autouse=True)
def web():
    with override_settings(
        SECRET_KEY='identity-tests-' + 'x' * 48,
        ROOT_URLCONF=__name__,
        DEBUG=False,
        ALLOWED_HOSTS=['testserver'],
        LOGIN_URL='/login/',
        TWO_FACTOR_ENCRYPTION_KEY=KEY,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='sender@example.com',
        PUBLIC_BASE_URL='https://finance.example.com',
        CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'login.middleware.TwoFactorSessionMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ],
        AUTHENTICATION_BACKENDS=[
            'django.contrib.auth.backends.ModelBackend',
            'social_core.backends.google.GoogleOAuth2',
        ],
        SOCIAL_LOGIN_ENABLED=True,
        SOCIAL_AUTH_GOOGLE_OAUTH2_KEY='client',
        SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET='secret',
        SOCIAL_AUTH_GOOGLE_OAUTH2_ID_KEY='sub',
        SOCIAL_AUTH_GOOGLE_OAUTH2_USE_UNIQUE_USER_ID=True,
        SOCIAL_AUTH_PIPELINE=(
            'social_core.pipeline.social_auth.social_details',
            'social_core.pipeline.social_auth.social_uid',
            'social_core.pipeline.social_auth.auth_allowed',
            'social_core.pipeline.social_auth.social_user',
            'login.pipeline.provision_user',
        ),
        SOCIAL_AUTH_LOGIN_REDIRECT_URL='/',
        SOCIAL_AUTH_NEW_ASSOCIATION_REDIRECT_URL='/usuarios/perfil/',
        REST_FRAMEWORK={'DEFAULT_AUTHENTICATION_CLASSES': [], 'DEFAULT_PERMISSION_CLASSES': []},
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': False,
                'OPTIONS': {
                    'loaders': [
                        ('django.template.loaders.locmem.Loader', {'index.html': '{% block content %}{% endblock %}'}),
                        'django.template.loaders.app_directories.Loader',
                    ],
                    'context_processors': [
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                        'login.context_processors.social_login',
                    ],
                },
            }
        ],
    ):
        cache.clear()
        mail.get_connection()
        mail.outbox.clear()
        yield
        cache.clear()


def account(**kwargs):
    return User.objects.create_user(
        username=kwargs.pop('username', 'owner'),
        name='Owner',
        email=kwargs.pop('email', 'old@example.com'),
        password='LocalPassword!123',
        **kwargs,
    )


def authenticated(user, *, recent=True):
    client = Client()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    session = client.session
    session['mfa_version'] = user.security_version
    session['mfa_verified_at'] = time.time() if recent else 0
    session['reauthenticated_at'] = time.time() if recent else 0
    session.save()
    return client


def enable(user):
    secret = b'12345678901234567890'
    TwoFactorDevice.objects.create(
        user=user, confirmed=True, encrypted_secret=security.cipher().encrypt(secret).decode()
    )
    user.two_factor_enabled = True
    user.save(update_fields=['two_factor_enabled'])
    return secret


def otp(secret):
    return f'{TOTP(secret).token():06d}'


def test_google_identity_can_have_different_email_and_metadata_contains_no_tokens():
    user = account()
    backend = type('Backend', (), {'name': 'google-oauth2'})()
    result = provision_user(
        backend,
        'google-stable',
        {'email': 'google@example.com'},
        {'email_verified': True, 'access_token': 'never-store'},
        user=user,
    )
    user.refresh_from_db()
    assert user.email == 'old@example.com'
    assert result['social'].uid == 'google-stable'
    assert result['social'].extra_data == {'email': 'google@example.com', 'email_verified': True}
    assert 'email' not in ProfileForm().fields
    assert 'email' in UserForm().fields


def test_email_change_is_pending_requires_mailbox_and_revokes_old_sessions():
    user = account(email_verified_at=timezone.now())
    client = authenticated(user)
    old = authenticated(user)
    response = client.post(BASE + 'email/', {'email': 'New@example.com'})
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.email == 'old@example.com' and user.pending_email == 'new@example.com'
    process_account_email()
    link = re.search(r'https://finance.example.com([^\s]+)', mail.outbox[0].body).group(1)
    assert mail.outbox[0].to == ['new@example.com']
    assert client.get(link).status_code == 200
    user.refresh_from_db()
    assert user.email == 'old@example.com'
    response = client.post(link)
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.email == 'new@example.com' and user.email_verified_at and not user.pending_email
    assert user.security_version == 1
    assert get_user(old).is_anonymous
    assert get_user(client).is_authenticated
    assert 'validlink' not in client.get(link).context or not client.get(link).context['validlink']
    assert process_account_email()
    assert mail.outbox[-1].to == ['old@example.com']


def test_email_confirmation_cannot_change_another_account_or_overwrite_existing_email():
    user = account()
    other = account(username='other', email='taken@example.com')
    client = authenticated(user)
    assert client.post(BASE + 'email/', {'email': 'TAKEN@example.com'}).status_code == 200
    assert not AccountEmailDelivery.objects.exists()
    client.post(BASE + 'email/', {'email': 'new@example.com'})
    process_account_email()
    link = re.search(r'https://finance.example.com([^\s]+)', mail.outbox[0].body).group(1)
    assert not authenticated(other).post(link).context['validlink']
    user.refresh_from_db()
    assert user.email == 'old@example.com'
    client.post(BASE + 'email/cancelar/')
    assert not client.post(link).context['validlink']


def test_email_change_needs_recent_authentication_and_csrf():
    user = account()
    assert (
        authenticated(user, recent=False)
        .post(BASE + 'email/', {'email': 'new@example.com'})
        .url.endswith('/confirmar-identidade/')
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    assert client.post(BASE + 'email/', {'email': 'new@example.com'}).status_code == 403
    assert not AccountEmailDelivery.objects.exists()


def test_enrollment_requires_verified_email_and_confirmed_code_then_shows_codes_once():
    user = account()
    client = authenticated(user)
    assert client.post(BASE + '2fa/configurar/', {'action': 'start'}).url == BASE
    assert not TwoFactorDevice.objects.exists()
    user.email_verified_at = timezone.now()
    user.save()
    client.post(BASE + '2fa/configurar/', {'action': 'start'})
    device = TwoFactorDevice.objects.get(user=user)
    assert not device.confirmed
    secret = security.secret_for(device, enrollment=True)
    assert secret.hex() not in device.pending_secret
    response = client.get(BASE + '2fa/configurar/')
    assert 'qr' in response.context and 'no-store' in response.headers['Cache-Control']
    response = client.post(BASE + '2fa/configurar/', {'code': otp(secret)})
    assert response.status_code == 200 and len(response.context['codes']) == 10
    user.refresh_from_db()
    assert user.two_factor_enabled and user.security_version == 1
    assert RecoveryCode.objects.filter(user=user).count() == 10
    assert all(code.digest not in response.context['codes'] for code in RecoveryCode.objects.all())
    assert get_user(client).is_authenticated
    assert client.get(BASE).context.get('codes') is None


def test_password_login_is_not_authenticated_before_second_factor():
    user = account()
    secret = enable(user)
    client = Client()
    response = client.post('/login/', {'username': user.username, 'password': 'LocalPassword!123'})
    assert response.url.endswith('/2fa/confirmar/')
    assert '_auth_user_id' not in client.session
    response = client.post(response.url, {'code': otp(secret)})
    assert response.status_code == 302
    assert client.session['_auth_user_id'] == str(user.pk)
    assert client.session['mfa_version'] == user.security_version
    assert 'pending_mfa' not in client.session
    assert not security.verify_factor(user, otp(secret))


def test_backup_code_is_one_time_and_only_hash_is_stored():
    user = account()
    enable(user)
    codes = security.generate_recovery_codes(user)
    assert security.verify_factor(user, codes[0])
    assert not security.verify_factor(user, codes[0])
    assert RecoveryCode.objects.count() == 9


def test_pending_challenge_expires_and_changes_in_password_or_epoch_invalidate_it():
    user = account()
    secret = enable(user)
    client = Client()
    client.post('/login/', {'username': user.username, 'password': 'LocalPassword!123'})
    session = client.session
    session['pending_mfa'] = {**session['pending_mfa'], 'at': time.time() - 301}
    session.save()
    assert client.post(BASE + '2fa/confirmar/', {'code': otp(secret)}).url == '/login/'
    client.post('/login/', {'username': user.username, 'password': 'LocalPassword!123'})
    user.set_password('ChangedPassword!123')
    user.save()
    assert client.post(BASE + '2fa/confirmar/', {'code': otp(secret)}).url == '/login/'
    assert '_auth_user_id' not in client.session


def test_authenticated_session_without_mfa_cannot_access_views_or_api():
    user = account()
    enable(user)
    client = Client()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    assert client.get('/api/private/').status_code == 403
    assert '_auth_user_id' not in client.session
    assert client.session.get('pending_mfa')


def test_jwt_requires_otp_and_refresh_is_invalidated_by_security_changes():
    user = account()
    secret = enable(user)
    client = Client()
    payload = {'username': user.username, 'password': 'LocalPassword!123'}
    assert client.post('/api/token/', payload).status_code in (401, 403)
    response = client.post('/api/token/', {**payload, 'otp': otp(secret)})
    assert response.status_code == 200
    tokens = response.json()
    auth = SecureJWTAuthentication()
    assert auth.get_user(auth.get_validated_token(tokens['access'])).pk == user.pk
    user.security_version += 1
    user.save()
    assert client.post('/api/token/refresh/', {'refresh': tokens['refresh']}).status_code in (401, 403)
    with pytest.raises(Exception):
        auth.get_user(auth.get_validated_token(tokens['access']))


def test_admin_requires_mfa_marker_and_uses_central_login():
    user = account(is_staff=True)
    enable(user)
    request = RequestFactory().get('/admin/')
    request.user = user
    request.session = {}
    admin = SecurityAdminSite()
    assert not admin.has_permission(request)
    request.session['mfa_version'] = user.security_version
    assert admin.has_permission(request)
    assert admin.login(request).url.startswith('/login/?next=')


def test_admin_recovery_is_audited_and_revokes_sessions():
    user = account()
    enable(user)
    client = authenticated(user)
    call_command('reset_two_factor', user.username, reason='Identidade confirmada presencialmente')
    user.refresh_from_db()
    assert not user.two_factor_enabled
    assert get_user(client).is_anonymous
    assert SecurityAuditEvent.objects.get().kind == 'administrative_2fa_recovery'


def test_password_recovery_keeps_two_factor_enabled():
    user = account()
    enable(user)
    client = Client()
    client.post('/usuarios/senha/recuperar/', {'email': user.email})
    from login.password_reset import process_delivery

    process_delivery()
    link = re.search(r'https://finance.example.com([^\s]+)', mail.outbox[0].body).group(1)
    hidden = client.get(link).url
    response = client.post(hidden, {'new_password1': 'NewPassword!123', 'new_password2': 'NewPassword!123'})
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.two_factor_enabled
    assert client.post('/login/', {'username': user.username, 'password': 'NewPassword!123'}).url.endswith(
        '/2fa/confirmar/'
    )


def test_google_login_defers_session_until_otp():
    user = account()
    secret = enable(user)
    UserSocialAuth.objects.create(user=user, provider='google-oauth2', uid='stable', id_key='sub')
    client = Client()
    response = client.post('/auth/login/google-oauth2/')
    from urllib.parse import parse_qs, urlsplit

    state = parse_qs(urlsplit(response.url).query)['state'][0]
    with patch(
        'social_core.backends.google.GoogleOAuth2.request_access_token', return_value={'access_token': 'fake'}
    ), patch(
        'social_core.backends.google.GoogleOAuth2.user_data',
        return_value={'sub': 'stable', 'email': 'google@example.com', 'email_verified': True},
    ):
        response = client.get('/auth/complete/google-oauth2/', {'state': state, 'code': 'fake'})
    assert response.url.endswith('/2fa/confirmar/')
    assert '_auth_user_id' not in client.session and 'google_reauthenticated' not in client.session
    client.post(response.url, {'code': otp(secret)})
    assert client.session['_auth_user_id'] == str(user.pk)
    assert client.session['google_reauthenticated']['user'] == str(user.pk)


def test_replacement_preserves_old_authenticator_until_confirmation():
    user = account(email_verified_at=timezone.now())
    old_secret = enable(user)
    client = authenticated(user)
    client.post(BASE + '2fa/configurar/', {'action': 'start'})
    device = TwoFactorDevice.objects.get(user=user)
    pending = security.secret_for(device, enrollment=True)
    assert security.secret_for(device) == old_secret and device.confirmed
    assert security.verify_factor(user, otp(old_secret))
    # The new device may confirm during the same time step as the previous one.
    result = client.post(BASE + '2fa/configurar/', {'code': otp(pending)})
    assert result.status_code == 200 and result.context['codes']
    assert security.secret_for(TwoFactorDevice.objects.get(user=user)) == pending


def test_disable_requires_a_factor_and_invalidates_other_sessions():
    user = account()
    secret = enable(user)
    client = authenticated(user)
    other = authenticated(user)
    assert client.post(BASE + '2fa/gerenciar/', {'action': 'disable'}).status_code == 302
    user.refresh_from_db()
    assert user.two_factor_enabled
    response = client.post(BASE + '2fa/gerenciar/', {'action': 'disable', 'code': otp(secret)})
    assert response.status_code == 302
    user.refresh_from_db()
    assert not user.two_factor_enabled
    assert not TwoFactorDevice.objects.exists()
    assert get_user(other).is_anonymous


def test_code_failures_throttle_and_missing_crypto_key_never_bypasses_2fa():
    user = account()
    secret = enable(user)
    assert not security.verify_factor(user, 'wrong')
    assert not security.verify_factor(user, otp(secret))
    TwoFactorDevice.objects.filter(user=user).update(locked_until=None)
    with override_settings(TWO_FACTOR_ENCRYPTION_KEY=''):
        assert not security.verify_factor(user, otp(secret))
    user.refresh_from_db()
    assert user.two_factor_enabled


def test_security_pages_preserve_origin_without_leaking_email_token_in_referrer():
    client = authenticated(account())
    response = client.get(BASE + 'email/confirmar/invalid/')
    assert response.headers['Referrer-Policy'] == 'strict-origin'
    assert 'no-store' in response.headers['Cache-Control']


def test_websocket_rejects_missing_mfa_and_revoked_session():
    from api.websockets.consumers.update_consumer import UpdateConsumer

    user = account()
    enable(user)
    consumer = UpdateConsumer()
    consumer.scope = {
        'user': user,
        'session': {'_auth_user_id': str(user.pk), '_auth_user_hash': user.get_session_auth_hash()},
    }
    # Inspect the sync policy without opening a socket or sharing transaction connections.
    check = lambda consumer: security.verified_websocket_session(consumer.scope)
    assert not check(consumer)
    consumer.scope['session']['mfa_version'] = user.security_version
    assert check(consumer)
    user.security_version += 1
    user.save()
    assert not check(consumer)


def test_oauth_password_grant_is_blocked_for_2fa_accounts():
    from django.apps import apps

    # The validator imports provider models; enable the app registry only for this policy check.
    from django.test import override_settings

    with override_settings(INSTALLED_APPS=[*settings.INSTALLED_APPS, 'oauth2_provider']):
        from login.oauth_validator import TwoFactorOAuthValidator

        user = account()
        enable(user)
        request = type('OAuthRequest', (), {'user': user})()
        with patch('oauth2_provider.oauth2_validators.OAuth2Validator.validate_user', return_value=True):
            assert not TwoFactorOAuthValidator().validate_user('owner', 'password', None, request)


def test_step_up_for_post_only_management_returns_to_review_not_405():
    user = account()
    secret = enable(user)
    client = authenticated(user, recent=False)
    response = client.post(BASE + '2fa/gerenciar/', {'action': 'disable', 'code': otp(secret)})
    assert response.url.endswith('/confirmar-identidade/')
    assert client.session['security_return'] == BASE
    response = client.post(response.url, {'password': 'LocalPassword!123', 'code': otp(secret)})
    assert response.url == BASE
    assert client.get(response.url).status_code == 200
    user.refresh_from_db()
    assert user.two_factor_enabled


def test_oauth_issuance_rechecks_two_factor_under_lock_after_password_validation():
    with override_settings(INSTALLED_APPS=[*settings.INSTALLED_APPS, 'oauth2_provider']):
        from login.oauth_validator import TwoFactorOAuthValidator
        from oauthlib.oauth2 import InvalidGrantError

        user = account()
        stale = User.objects.get(pk=user.pk)
        enable(user)
        request = type('OAuthRequest', (), {'user': stale, 'grant_type': 'password'})()
        with patch('oauth2_provider.oauth2_validators.OAuth2Validator.save_bearer_token') as save:
            with pytest.raises(InvalidGrantError):
                TwoFactorOAuthValidator().save_bearer_token({}, request)
            save.assert_not_called()
