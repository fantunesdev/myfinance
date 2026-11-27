from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError

from clients.pluggy.reader import ProbeError
from login.models import User


@pytest.fixture
def command_env(bank_case, monkeypatch, mocker, settings, tmp_path):
    settings.BASE_DIR = tmp_path
    monkeypatch.delenv('PLUGGY_ITEM_ID', raising=False)
    mocker.patch(
        'bank_sync.management.commands.sync_pluggy.dotenv_values',
        return_value={'PLUGGY_ITEM_ID': str(bank_case.connection.item_id)},
    )
    return bank_case


def test_sync_command_requires_an_explicit_existing_active_owner(command_env):
    with pytest.raises(CommandError, match='username'):
        call_command('sync_pluggy', username='missing')


def test_sync_command_never_takes_a_connection_owned_by_someone_else(command_env):
    User.objects.create(username='other-owner', email='other-owner@test.invalid')
    with pytest.raises(CommandError, match='outro usuário'):
        call_command('sync_pluggy', username='other-owner')


def test_sync_command_reports_the_number_of_source_occurrences(command_env, mocker):
    sync = mocker.patch(
        'bank_sync.management.commands.sync_pluggy.sync_connection', return_value=SimpleNamespace(transaction_count=42)
    )
    output = StringIO()
    call_command('sync_pluggy', username=command_env.user.username, stdout=output)
    assert '42 ocorrências' in output.getvalue()
    assert sync.call_args.args[0] == command_env.connection


@pytest.mark.parametrize('error', [ProbeError('incomplete'), ValidationError('invalid')])
def test_sync_command_converts_safe_diagnostics_to_command_errors(command_env, mocker, error):
    mocker.patch('bank_sync.management.commands.sync_pluggy.sync_connection', side_effect=error)
    with pytest.raises(CommandError):
        call_command('sync_pluggy', username=command_env.user.username)


def test_sync_command_rejects_missing_or_invalid_item_identifier(command_env, monkeypatch):
    monkeypatch.setenv('PLUGGY_ITEM_ID', 'invalid')
    with pytest.raises(CommandError, match='PLUGGY_ITEM_ID'):
        call_command('sync_pluggy', username=command_env.user.username)


def test_history_reconciliation_command_reports_missing_connections(db):
    with pytest.raises(CommandError):
        call_command('reconcile_investment_history', connection=999999)


def test_history_reconciliation_command_reports_validation_failures(bank_case, mocker):
    mocker.patch(
        'bank_sync.management.commands.reconcile_investment_history.auto_reconcile',
        side_effect=ValidationError('incomplete'),
    )
    with pytest.raises(CommandError):
        call_command('reconcile_investment_history', connection=bank_case.connection.pk)
