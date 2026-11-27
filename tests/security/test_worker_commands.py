import io
import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.parametrize('processed', [False, True])
def test_mail_worker_handles_idle_waiting_and_keyboard_interrupt(mocker, processed):
    module = 'login.management.commands.process_password_reset_emails'
    mocker.patch(f'{module}.close_old_connections')
    mocker.patch(f'{module}.process_delivery', side_effect=[processed, False])
    mocker.patch(f'{module}.process_account_email', return_value=False)
    sleep = mocker.patch(f'{module}.time.sleep', side_effect=KeyboardInterrupt)
    call_command('process_password_reset_emails')
    sleep.assert_called_once_with(2)


@pytest.mark.parametrize('reason', ['short', 'unknown', 'disabled'])
@pytest.mark.django_db
def test_admin_factor_reset_rejects_incomplete_or_ineligible_requests(reason):
    from login.models import User

    user = User.objects.create(username='factor-reset-edge', email='factor-reset-edge@test.invalid')
    with pytest.raises(CommandError):
        call_command(
            'reset_two_factor',
            'missing' if reason == 'unknown' else user.username,
            reason='short' if reason == 'short' else 'Justificativa administrativa',
        )


@pytest.mark.parametrize('payload', [None, {}, {'web': {}}, 'invalid'])
def test_gmail_authorization_rejects_invalid_client_configuration(tmp_path, payload):
    source = tmp_path / 'client.json'
    source.write_text('invalid' if payload == 'invalid' else json.dumps(payload))
    with pytest.raises(CommandError):
        call_command('authorize_gmail', client_file=str(source), output=str(tmp_path / 'token.json'))


def test_gmail_authorization_requires_the_registered_callback_uri(tmp_path):
    source = tmp_path / 'client.json'
    source.write_text(json.dumps({'web': {'client_id': 'test', 'client_secret': 'test', 'redirect_uris': []}}))
    with pytest.raises(CommandError, match='Cadastre'):
        call_command('authorize_gmail', client_file=str(source), output=str(tmp_path / 'token.json'))


@pytest.mark.parametrize('failure', ['cancelled', 'invalid_state', 'missing_offline_token', 'transport'])
def test_gmail_authorization_handles_callback_and_token_exchange_failures(tmp_path, mocker, failure):
    module = 'login.management.commands.authorize_gmail'
    source = tmp_path / 'client.json'
    source.write_text(
        json.dumps(
            {
                'web': {
                    'client_id': 'test',
                    'client_secret': 'test',
                    'redirect_uris': ['http://localhost:8766/oauth/gmail/callback/'],
                }
            }
        )
    )
    oauth = mocker.Mock()
    oauth.authorization_url.return_value = ('https://google.invalid/authorize', 'expected-state')
    oauth.fetch_token.return_value = {}
    if failure == 'transport':
        oauth.fetch_token.side_effect = RuntimeError('unavailable')
    mocker.patch(f'{module}.OAuth2Session', return_value=oauth)
    ticks = iter([0, 1, 301])
    mocker.patch(f'{module}.time.monotonic', side_effect=lambda: next(ticks, 301))

    def server(address, handler):
        instance = mocker.MagicMock()
        instance.__enter__.return_value = instance

        def callback():
            request = handler.__new__(handler)
            request.path = '/oauth/gmail/callback/?state=' + (
                'invalid' if failure == 'invalid_state' else 'expected-state'
            )
            request.path += '&error=access_denied' if failure == 'cancelled' else '&code=test-code'
            request.wfile = io.BytesIO()
            request.send_response = mocker.Mock()
            request.send_header = mocker.Mock()
            request.end_headers = mocker.Mock()
            request.log_message('no callback secrets in logs')
            request.do_GET()

        instance.handle_request.side_effect = callback
        return instance

    mocker.patch(f'{module}.HTTPServer', side_effect=server)
    target = tmp_path / 'token.json'
    with pytest.raises(CommandError):
        call_command('authorize_gmail', client_file=str(source), output=str(target), stdout=io.StringIO())
    assert not target.exists()
