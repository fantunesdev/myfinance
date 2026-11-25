import base64
import io
import json
import re
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpResponse
from django.test import Client, override_settings
from django.urls import include, path
from django.utils import timezone
from social_django.models import UserSocialAuth

from login.email_backend import GmailBackend, GmailDeliveryError
from login.models import PasswordResetDelivery, Profile, User
from login.password_reset import process_delivery

urlpatterns = [
    path('usuarios/senha/', include('login.recovery_urls')),
    path('login/', lambda request: HttpResponse('login'), name='login_user'),
    path('private/', login_required(lambda request: HttpResponse('private'))),
]
pytestmark = pytest.mark.django_db
REQUEST = '/usuarios/senha/recuperar/'


@pytest.fixture(autouse=True)
def recovery_settings():
    with override_settings(
        ROOT_URLCONF=__name__,
        DEBUG=False,
        ALLOWED_HOSTS=['testserver'],
        LOGIN_URL='/login/',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='MyFinance <sender@example.com>',
        PUBLIC_BASE_URL='https://finance.example.com',
        PASSWORD_RESET_TIMEOUT=1800,
        PASSWORD_RESET_IP_LIMIT=30,
        PASSWORD_RESET_EMAIL_LIMIT=3,
        CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
        AUTH_PASSWORD_VALIDATORS=[{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}],
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ],
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
                'OPTIONS': {'context_processors': ['django.template.context_processors.request']},
            }
        ],
    ):
        cache.clear()
        mail.get_connection()
        mail.outbox.clear()
        yield
        cache.clear()


def user(**kwargs):
    return User.objects.create_user(
        username='recovery',
        email='recovery@example.com',
        name='Recovery',
        password=kwargs.pop('password', 'OldPassword!123'),
        **kwargs
    )


def submit(client=None, email='recovery@example.com'):
    client = client or Client()
    response = client.post(REQUEST, {'email': email})
    assert response.status_code == 302
    return client


def emailed_path():
    assert len(mail.outbox) == 1
    return re.search(r'https://finance.example.com([^\s]+)', mail.outbox[0].body).group(1)


def test_request_queues_without_sending_then_worker_uses_configured_origin():
    account = user()
    client = Client()
    response = client.post(REQUEST, {'email': 'RECOVERY@example.com'}, HTTP_HOST='testserver')
    assert response.url.endswith('/recuperar/enviado/')
    assert not mail.outbox
    item = PasswordResetDelivery.objects.get()
    assert item.user == account and account.email not in item.credential_fingerprint
    assert not any(f.name in ('token', 'email', 'reset_url') for f in item._meta.fields)
    assert process_delivery()
    assert not PasswordResetDelivery.objects.exists()
    assert mail.outbox[0].to == ['recovery@example.com']
    assert 'testserver' not in mail.outbox[0].body
    assert '/usuarios/senha/recuperar/' in emailed_path()
    assert not process_delivery()


@pytest.mark.parametrize('kind', ['missing', 'inactive', 'social'])
def test_ineligible_requests_have_same_public_response_and_no_email(kind):
    if kind != 'missing':
        user(password=None if kind == 'social' else 'OldPassword!123', is_active=kind != 'inactive')
    client = submit()
    assert 'Se houver uma conta elegível' in client.get(REQUEST + 'enviado/').content.decode()
    assert PasswordResetDelivery.objects.count() == 1
    assert process_delivery()
    assert not mail.outbox and not PasswordResetDelivery.objects.exists()


def test_reset_changes_password_invalidates_sessions_preserves_google_and_preference():
    account = user()
    profile = Profile.objects.create(user=account, social_login_enabled=False)
    social = UserSocialAuth.objects.create(user=account, provider='google-oauth2', uid='stable', id_key='sub')
    browser = Client()
    browser.force_login(account)
    assert browser.get('/private/').status_code == 200
    submit()
    process_delivery()
    client = Client()
    link = emailed_path()
    hidden = client.get(link)
    assert hidden.status_code == 302 and 'set-password' in hidden.url
    assert client.get(hidden.url).status_code == 200
    response = client.post(hidden.url, {'new_password1': 'NewPassword!123', 'new_password2': 'NewPassword!123'})
    assert response.url.endswith('/recuperar/concluido/')
    account.refresh_from_db()
    assert account.check_password('NewPassword!123') and not account.check_password('OldPassword!123')
    assert '_auth_user_id' not in client.session
    assert browser.get('/private/').status_code == 302
    assert 'inválido' in Client().get(link).content.decode()
    assert UserSocialAuth.objects.get(pk=social.pk).user == account
    profile.refresh_from_db()
    assert not profile.social_login_enabled


def test_expired_tampered_and_inactive_links_are_rejected():
    account = user()
    submit()
    process_delivery()
    path = emailed_path()
    assert 'inválido' in Client().get(path.replace(path.split('/')[-2], 'tampered')).content.decode()
    with override_settings(PASSWORD_RESET_TIMEOUT=-1):
        assert 'inválido' in Client().get(path).content.decode()
    account.is_active = False
    account.save()
    assert 'inválido' in Client().get(path).content.decode()


def test_password_rules_and_csrf():
    user()
    client = Client(enforce_csrf_checks=True)
    assert client.post(REQUEST, {'email': 'recovery@example.com'}).status_code == 403
    client.get(REQUEST)
    csrf = client.cookies['csrftoken'].value
    client.post(REQUEST, {'email': 'recovery@example.com'}, HTTP_X_CSRFTOKEN=csrf)
    process_delivery()
    hidden = client.get(emailed_path()).url
    client.get(hidden)
    assert client.post(hidden, {'new_password1': 'ValidPass!123', 'new_password2': 'ValidPass!123'}).status_code == 403
    csrf = client.cookies['csrftoken'].value
    response = client.post(hidden, {'new_password1': 'short', 'new_password2': 'short'}, HTTP_X_CSRFTOKEN=csrf)
    assert response.status_code == 200 and response.context['form'].errors
    response = client.post(
        hidden, {'new_password1': 'ValidPass!123', 'new_password2': 'different'}, HTTP_X_CSRFTOKEN=csrf
    )
    assert response.status_code == 200 and response.context['form'].errors
    assert User.objects.get().check_password('OldPassword!123')


def test_email_and_ip_limits_do_not_disclose_accounts():
    user()
    with override_settings(PASSWORD_RESET_EMAIL_LIMIT=2, PASSWORD_RESET_IP_LIMIT=3):
        submit(email='recovery@example.com')
        submit(email='RECOVERY@example.com')
        submit(email='recovery@example.com')
        assert PasswordResetDelivery.objects.count() == 2
        submit(email='different@example.com')
        assert PasswordResetDelivery.objects.count() == 2
    keys = list(cache._cache)
    assert all('recovery@' not in key and '127.0.0.1' not in key for key in keys)


def test_cache_and_enqueue_failures_keep_same_public_result(caplog):
    user()
    with patch('login.password_reset.cache.add', side_effect=RuntimeError('private details')):
        submit()
    assert not PasswordResetDelivery.objects.exists()
    with patch.object(PasswordResetDelivery.objects, 'create', side_effect=RuntimeError('private details')):
        submit()
    assert 'private details' not in caplog.text


@pytest.mark.parametrize('change', ['password', 'email', 'inactive'])
def test_queued_request_does_not_send_after_account_changes(change):
    account = user()
    submit()
    if change == 'password':
        account.set_password('OtherPassword!123')
    elif change == 'email':
        account.email = 'changed@example.com'
    else:
        account.is_active = False
    account.save()
    process_delivery()
    assert not mail.outbox and not PasswordResetDelivery.objects.exists()


def test_expired_queue_item_is_discarded():
    user()
    submit()
    PasswordResetDelivery.objects.update(created_at=timezone.now() - timedelta(minutes=31))
    assert not process_delivery()
    assert not mail.outbox and not PasswordResetDelivery.objects.exists()


def test_failures_retry_and_expired_lease_recovers_without_logging_provider_details(caplog):
    user()
    submit()
    with patch('login.password_reset.EmailMultiAlternatives.send', side_effect=RuntimeError('secret-token')):
        process_delivery()
        item = PasswordResetDelivery.objects.get()
        assert item.attempts == 1 and item.available_at > timezone.now()
        assert not process_delivery()
        PasswordResetDelivery.objects.update(
            available_at=timezone.now(), locked_until=timezone.now() - timedelta(seconds=1)
        )
        process_delivery()
        PasswordResetDelivery.objects.update(available_at=timezone.now())
        process_delivery()
    assert not PasswordResetDelivery.objects.exists()
    assert 'secret-token' not in caplog.text


def test_active_lease_is_not_processed():
    user()
    submit()
    PasswordResetDelivery.objects.update(locked_until=timezone.now() + timedelta(minutes=1))
    assert not process_delivery()
    assert not mail.outbox


def test_public_origin_must_be_https_without_request_host_fallback(caplog):
    user()
    submit()
    with override_settings(PUBLIC_BASE_URL='http://evil.example.com'):
        process_delivery()
    assert not mail.outbox
    assert PasswordResetDelivery.objects.get().attempts == 1
    assert 'evil.example.com' not in caplog.text


def test_worker_once_uses_queue_without_touching_real_email():
    user()
    submit()
    call_command('process_password_reset_emails', once=True)
    assert len(mail.outbox) == 1


def test_gmail_backend_refreshes_and_encodes_mime_without_exposing_bcc():
    responses = [
        SimpleNamespace(
            raise_for_status=lambda: None, json=lambda: {'access_token': 'test-access', 'expires_in': 3600}
        ),
        SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'id': 'message-1'}),
        SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'id': 'message-2'}),
    ]
    with override_settings(
        GMAIL_CLIENT_ID='test-client',
        GMAIL_CLIENT_SECRET='test-secret',
        GMAIL_REFRESH_TOKEN='test-refresh',
        GMAIL_SENDER_EMAIL='sender@example.com',
    ):
        with patch('login.email_backend.requests.post', side_effect=responses) as post:
            message = mail.EmailMessage('Olá', 'Mensagem de teste', settings.DEFAULT_FROM_EMAIL, ['to@example.com'])
            backend = GmailBackend()
            assert backend.send_messages([message, message]) == 2
            assert post.call_count == 3
            refresh_call, send_call, _ = post.call_args_list
            assert refresh_call.kwargs['data']['grant_type'] == 'refresh_token'
            assert send_call.kwargs['headers']['Authorization'] == 'Bearer test-access'
            payload = base64.urlsafe_b64decode(send_call.kwargs['json']['raw'])
            assert b'To: to@example.com' in payload and b'From: MyFinance' in payload


def test_gmail_backend_failure_and_silent_failure_never_expose_secrets():
    with override_settings(
        GMAIL_CLIENT_ID='test-client',
        GMAIL_CLIENT_SECRET='test-secret',
        GMAIL_REFRESH_TOKEN='test-refresh',
        GMAIL_SENDER_EMAIL='sender@example.com',
    ):
        with patch('login.email_backend.requests.post', side_effect=RuntimeError('provider-secret')):
            message = mail.EmailMessage('Subject', 'Body', settings.DEFAULT_FROM_EMAIL, ['to@example.com'])
            with pytest.raises(GmailDeliveryError) as exc:
                GmailBackend().send_messages([message])
            assert 'provider-secret' not in str(exc.value)
            assert exc.value.__suppress_context__
            assert GmailBackend(fail_silently=True).send_messages([message]) == 0


def test_gmail_authorization_validates_state_and_saves_private_refresh_file(tmp_path):
    client_file = tmp_path / 'client.json'
    client_file.write_text(
        json.dumps(
            {
                'web': {
                    'client_id': 'test-client',
                    'client_secret': 'test-secret',
                    'redirect_uris': ['http://localhost:8766/oauth/gmail/callback/'],
                }
            }
        )
    )
    output = tmp_path / 'token.json'
    stdout = io.StringIO()
    oauth = MagicMock()
    oauth.authorization_url.return_value = ('https://accounts.google.com/authorize?state=test-state', 'test-state')
    oauth.fetch_token.return_value = {
        'refresh_token': 'private-refresh',
        'scope': ['https://www.googleapis.com/auth/gmail.send'],
    }

    def create_server(address, handler):
        server = MagicMock()
        server.__enter__.return_value = server

        def callback():
            request = handler.__new__(handler)
            request.path = '/oauth/gmail/callback/?state=test-state&code=test-code'
            request.wfile = io.BytesIO()
            request.send_response = MagicMock()
            request.send_header = MagicMock()
            request.end_headers = MagicMock()
            request.do_GET()

        server.handle_request.side_effect = callback
        return server

    with patch('login.management.commands.authorize_gmail.OAuth2Session', return_value=oauth), patch(
        'login.management.commands.authorize_gmail.HTTPServer',
        side_effect=create_server,
    ):
        call_command('authorize_gmail', client_file=str(client_file), output=str(output), stdout=stdout)
    assert json.loads(output.read_text())['refresh_token'] == 'private-refresh'
    assert output.stat().st_mode & 0o777 == 0o600
    assert 'private-refresh' not in stdout.getvalue()
    with pytest.raises(CommandError):
        call_command('authorize_gmail', client_file=str(client_file), output=str(output))


def test_recovery_pages_prevent_caching_and_referrer_leaks():
    client = Client()
    for url in (REQUEST, REQUEST + 'enviado/', REQUEST + 'concluido/', REQUEST + 'invalid/invalid/'):
        response = client.get(url)
        assert response.status_code == 200
        assert response.headers['Cache-Control'] == 'no-store' or 'no-store' in response.headers['Cache-Control']
        assert response.headers['Referrer-Policy'] == 'strict-origin'


def test_application_log_filter_redacts_reset_credentials():
    import logging
    from login.log_filters import RecoveryURLFilter

    record = logging.LogRecord(
        'django.server', logging.INFO, '', 1, 'GET %s HTTP/1.1', ('/usuarios/senha/recuperar/uid/private-token/',), None
    )
    assert RecoveryURLFilter().filter(record)
    assert 'private-token' not in record.getMessage() and '[redacted]' in record.getMessage()


def test_configuration_checks_identify_missing_gmail_and_bad_origin():
    from login.checks import password_recovery_configuration

    with override_settings(
        EMAIL_BACKEND='login.email_backend.GmailBackend',
        GMAIL_CLIENT_ID='',
        GMAIL_CLIENT_SECRET='',
        GMAIL_SENDER_EMAIL='',
        GMAIL_REFRESH_TOKEN='',
        GMAIL_REFRESH_TOKEN_FILE='',
        PUBLIC_BASE_URL='',
        EMAIL_TIMEOUT=60,
    ):
        codes = {check.id for check in password_recovery_configuration(None)}
        assert {'login.W001', 'login.W002', 'login.E002'} <= codes


def test_gmail_refresh_token_file_is_supported(tmp_path):
    target = tmp_path / 'private.json'
    target.write_text(json.dumps({'refresh_token': 'file-refresh'}))
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'access_token': 'access', 'expires_in': 1})
    with override_settings(
        GMAIL_REFRESH_TOKEN_FILE=str(target),
        GMAIL_REFRESH_TOKEN='',
        GMAIL_CLIENT_ID='client',
        GMAIL_CLIENT_SECRET='secret',
    ):
        with patch('login.email_backend.requests.post', return_value=response) as post:
            backend = GmailBackend()
            backend.refresh()
            assert post.call_args.kwargs['data']['refresh_token'] == 'file-refresh'
            assert backend.access_token == 'access'


def test_ambiguous_legacy_email_addresses_do_not_reset_arbitrary_accounts():
    user()
    User.objects.create_user(username='ambiguous', email='RECOVERY@example.com', name='Other', password='Other!123')
    submit()
    process_delivery()
    assert not mail.outbox


def test_reset_rechecks_consumed_token_when_form_is_already_open():
    user()
    submit()
    process_delivery()
    link = emailed_path()
    first, second = Client(), Client()
    first_form, second_form = first.get(link).url, second.get(link).url
    assert (
        first.post(first_form, {'new_password1': 'First!Password123', 'new_password2': 'First!Password123'}).status_code
        == 302
    )
    response = second.post(second_form, {'new_password1': 'Second!Password123', 'new_password2': 'Second!Password123'})
    assert response.status_code == 200 and 'inválido' in response.content.decode()
    assert User.objects.get().check_password('First!Password123')
