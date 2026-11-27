import base64
import time
from types import SimpleNamespace

import pytest
from django.core.mail import EmailMessage
from django.test import RequestFactory, override_settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework_simplejwt.tokens import RefreshToken

from login.api_auth import SecureRefreshSerializer
from login.authentication import SecureSessionAuthentication
from login.checks import password_recovery_configuration
from login.email_backend import GmailBackend, GmailDeliveryError
from login.models import User


@pytest.fixture
def identity(db):
    return User.objects.create_user('auth-edge', 'auth-edge@test.invalid', 'Auth', 'Password!123')


@pytest.mark.parametrize('state', ['anonymous', 'plain', 'verified', 'missing_mfa'])
def test_session_authentication_requires_the_current_mfa_marker(identity, state):
    from django.contrib.auth.models import AnonymousUser

    raw = RequestFactory().get('/api/')
    identity.two_factor_enabled = state in ('verified', 'missing_mfa')
    identity.save()
    raw.user = AnonymousUser() if state == 'anonymous' else identity
    raw.session = {'mfa_version': identity.security_version} if state == 'verified' else {}
    if state == 'missing_mfa':
        with pytest.raises(PermissionDenied):
            SecureSessionAuthentication().authenticate(Request(raw))
    else:
        result = SecureSessionAuthentication().authenticate(Request(raw))
        assert result == (None if state == 'anonymous' else (identity, None))


def test_healthy_refresh_token_can_issue_a_new_access_token(identity):
    refresh = RefreshToken.for_user(identity)
    refresh['security_version'] = identity.security_version
    refresh['amr'] = ['pwd']
    assert SecureRefreshSerializer().validate({'refresh': str(refresh)})['access']


def test_recovery_configuration_reports_nonpositive_limits_and_invalid_crypto_key(settings):
    settings.PUBLIC_BASE_URL = 'https://finance.invalid'
    settings.PASSWORD_RESET_TIMEOUT = -1
    settings.TWO_FACTOR_ENCRYPTION_KEY = 'invalid'
    issues = password_recovery_configuration(None)
    assert {'login.E001', 'login.E003'} <= {issue.id for issue in issues}


def test_gmail_refresh_requires_complete_sender_credentials(settings):
    settings.GMAIL_CLIENT_ID = ''
    settings.GMAIL_CLIENT_SECRET = ''
    settings.GMAIL_REFRESH_TOKEN = ''
    settings.GMAIL_REFRESH_TOKEN_FILE = ''
    with pytest.raises(GmailDeliveryError):
        GmailBackend().refresh()


def test_gmail_skips_messages_without_recipients():
    assert GmailBackend().send_messages([EmailMessage('Subject', 'Body', 'sender@test.invalid')]) == 0


@pytest.mark.parametrize('confirmed', [True, False])
def test_gmail_includes_bcc_in_the_raw_payload_and_requires_delivery_confirmation(settings, mocker, confirmed):
    settings.GMAIL_SENDER_EMAIL = 'sender@test.invalid'
    response = mocker.Mock()
    response.json.return_value = {'id': 'sent-id'} if confirmed else {}
    send = mocker.patch('login.email_backend.requests.post', return_value=response)
    backend = GmailBackend()
    backend.access_token = 'disposable-access'
    backend.expires_at = time.monotonic() + 3600
    message = EmailMessage('Subject', 'Body', 'sender@test.invalid', ['to@test.invalid'], bcc=['blind@test.invalid'])
    if confirmed:
        assert backend.send_messages([message]) == 1
    else:
        with pytest.raises(GmailDeliveryError):
            backend.send_messages([message])
    raw = base64.urlsafe_b64decode(send.call_args.kwargs['json']['raw']).decode()
    assert 'Bcc: blind@test.invalid' in raw


@pytest.mark.parametrize('grant', ['client_credentials', 'password', 'refresh_token', 'authorization_code'])
def test_oauth_issuance_revalidates_the_relevant_user_grant(identity, settings, mocker, grant):
    with override_settings(INSTALLED_APPS=[*settings.INSTALLED_APPS, 'oauth2_provider']):
        from login.oauth_validator import TwoFactorOAuthValidator

        parent = mocker.patch(
            'oauth2_provider.oauth2_validators.OAuth2Validator.save_bearer_token', return_value='saved'
        )
        mocker.patch('oauth2_provider.models.RefreshToken.objects.filter').return_value.exists.return_value = True
        mocker.patch('oauth2_provider.models.Grant.objects.filter').return_value.exists.return_value = True
        request = SimpleNamespace(user=identity, grant_type=grant, refresh_token='refresh', code='code')
        assert TwoFactorOAuthValidator().save_bearer_token({}, request) == 'saved'
        parent.assert_called_once()


@pytest.mark.parametrize('grant, model', [('refresh_token', 'RefreshToken'), ('authorization_code', 'Grant')])
def test_oauth_issuance_rejects_a_revoked_grant(identity, settings, mocker, grant, model):
    from oauthlib.oauth2 import InvalidGrantError

    with override_settings(INSTALLED_APPS=[*settings.INSTALLED_APPS, 'oauth2_provider']):
        from login.oauth_validator import TwoFactorOAuthValidator

        parent = mocker.patch('oauth2_provider.oauth2_validators.OAuth2Validator.save_bearer_token')
        mocker.patch(f'oauth2_provider.models.{model}.objects.filter').return_value.exists.return_value = False
        request = SimpleNamespace(user=identity, grant_type=grant, refresh_token='refresh', code='code')
        with pytest.raises(InvalidGrantError):
            TwoFactorOAuthValidator().save_bearer_token({}, request)
        parent.assert_not_called()


def test_oauth_user_validation_preserves_parent_rejection(identity, settings, mocker):
    with override_settings(INSTALLED_APPS=[*settings.INSTALLED_APPS, 'oauth2_provider']):
        from login.oauth_validator import TwoFactorOAuthValidator

        mocker.patch('oauth2_provider.oauth2_validators.OAuth2Validator.validate_user', return_value=False)
        assert not TwoFactorOAuthValidator().validate_user('invalid', 'invalid', None, SimpleNamespace(user=identity))
