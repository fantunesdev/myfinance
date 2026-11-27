import runpy
from pathlib import Path

import pytest

from myfinance.environment import env_bool
from statement.repositories import vault_repository

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    'debug, proxy, backend',
    [
        ('true', 'true', 'django.core.mail.backends.console.EmailBackend'),
        ('false', 'false', 'login.email_backend.GmailBackend'),
    ],
)
def test_deployment_settings_derive_security_and_mail_defaults_without_loading_dotenv(
    mocker, monkeypatch, debug, proxy, backend
):
    mocker.patch('dotenv.load_dotenv')
    for key in ['PUBLIC_BASE_URL', 'EMAIL_BACKEND', 'EMAIL_TIMEOUT', 'DEFAULT_FROM_EMAIL', 'GMAIL_SENDER_EMAIL']:
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        'HOSTS': 'finance.invalid,localhost',
        'CORS_ALLOWED_ORIGINS': 'https://finance.invalid',
        'CSRF_TRUSTED_ORIGINS': 'https://finance.invalid',
        'ACCESS_TOKEN_EXPIRE_MINUTES': '15',
        'DEBUG': debug,
        'TRUST_HTTPS_PROXY': proxy,
        'SECRET_KEY': 'test-config-only',
    }.items():
        monkeypatch.setenv(key, value)
    config = runpy.run_path(str(ROOT / 'myfinance/settings.py'))
    assert config['DEBUG'] is (debug == 'true')
    assert config['ALLOWED_HOSTS'] == ['finance.invalid', 'localhost']
    assert ('SECURE_PROXY_SSL_HEADER' in config) is (proxy == 'true')
    assert config['MAILERS']['default']['BACKEND'] == backend
    assert config['MAILERS']['default']['OPTIONS'] == ({} if debug == 'true' else {'timeout': 15})
    assert config['REST_FRAMEWORK']['DEFAULT_PERMISSION_CLASSES'] == ['rest_framework.permissions.IsAuthenticated']
    assert config['PUBLIC_BASE_URL'] == ('http://localhost:8000' if debug == 'true' else '')


def test_environment_boolean_uses_default_only_when_missing(monkeypatch):
    monkeypatch.delenv('MYFINANCE_COVERAGE_BOOL', raising=False)
    assert env_bool('MYFINANCE_COVERAGE_BOOL', default=True)
    monkeypatch.setenv('MYFINANCE_COVERAGE_BOOL', 'not-a-boolean')
    with pytest.raises(ValueError):
        env_bool('MYFINANCE_COVERAGE_BOOL')


@pytest.mark.parametrize(
    'engine, function, prefix',
    [
        ('mysql', vault_repository.export_mysql_credentials, 'MYSQL'),
        ('postgresql', vault_repository.export_postgre_credentials, 'POSTGRESQL'),
    ],
)
def test_vault_credentials_retry_after_vault_restarts(mocker, monkeypatch, engine, function, prefix):
    monkeypatch.setenv('URL', 'http://vault.invalid')
    monkeypatch.setenv(f'{prefix}_USER', '')
    monkeypatch.setenv(f'{prefix}_PASSWORD', '')
    client = mocker.Mock()
    client.kv.v1.read_secret.side_effect = [
        {'data': {'user': 'disposable-user'}},
        {'data': {'password': 'disposable-password'}},
    ]
    factory = mocker.patch.object(
        vault_repository.hvac, 'Client', side_effect=[vault_repository.hvac.exceptions.VaultDown(), client]
    )
    restart = mocker.patch.object(vault_repository.os, 'system', return_value=0)
    function()
    restart.assert_called_once_with('vaultctl -u')
    assert factory.call_count == 2
    assert client.kv.v1.read_secret.call_args_list == [mocker.call(f'{engine}/user'), mocker.call(f'{engine}/password')]
    assert vault_repository.os.environ[f'{prefix}_USER'] == 'disposable-user'
    assert vault_repository.os.environ[f'{prefix}_PASSWORD'] == 'disposable-password'


def test_wsgi_entrypoint_exports_the_django_application(mocker):
    app = mocker.Mock()
    mocker.patch('django.core.wsgi.get_wsgi_application', return_value=app)
    module = runpy.run_path(str(ROOT / 'myfinance/wsgi.py'))
    assert module['application'] is app


def test_asgi_entrypoint_routes_http_and_authenticated_websockets(mocker):
    app = mocker.Mock()
    mocker.patch('django.core.asgi.get_asgi_application', return_value=app)
    module = runpy.run_path(str(ROOT / 'myfinance/asgi.py'))
    assert module['application'].application_mapping['http'] is app
    assert 'websocket' in module['application'].application_mapping
