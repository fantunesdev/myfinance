from datetime import timedelta
from uuid import uuid4

import pytest
import test_integration as scenarios
from django.core.exceptions import ValidationError
from django.utils import timezone

from bank_sync.models import BankConnection, ExternalAccount, ExternalBill, ExternalTransaction, SyncRun
from bank_sync.reconciliation import classify, event_kind
from bank_sync.services import configured_reader, confirm, money, sync_connection
from statement.models import AppConfig, Transaction


@pytest.fixture
def card_source(db):
    case = scenarios.PluggyIntegrationTests()
    case.setUp()
    return case


def test_confirmed_account_mapping_cannot_be_reassigned_to_another_card(card_source):
    from bank_sync.services import map_account
    from statement.models import Card

    c = card_source
    row = c.mapped()
    confirm(c.user, row.pk, row.revision, 'create', c.create_data())
    other = Card.objects.create(
        user=c.user, flag=c.card.flag, description='Outro cartão', closing_day=3, expiration_day=10
    )
    with pytest.raises(ValidationError):
        map_account(c.user, row.account_id, other.pk, {})


@pytest.mark.parametrize('confirmed', [True, False])
def test_card_identifier_remapping_requires_review_of_confirmed_occurrences(card_source, confirmed):
    from bank_sync.services import map_account
    from statement.models import CardNumber

    c = card_source
    row = c.mapped()
    if confirmed:
        confirm(c.user, row.pk, row.revision, 'create', c.create_data())
    number = CardNumber.objects.create(card=c.card, number='5678')
    if confirmed:
        with pytest.raises(ValidationError):
            map_account(c.user, row.account_id, c.card.pk, {'1234': number.pk})
    else:
        map_account(c.user, row.account_id, c.card.pk, {'1234': number.pk})
        row.refresh_from_db()
        assert row.revision == 2


@pytest.mark.parametrize('invalid', ['forecast', 'closing_days'])
def test_invalid_estimated_due_dates_require_manual_correction(card_source, invalid):
    from bank_sync.services import payment_due_date

    c = card_source
    row = c.mapped()
    row.facts.update(
        bill_id='', forecast='2026-02invalid' if invalid == 'forecast' else '', date='2026-02-01', purchase_date=''
    )
    if invalid == 'closing_days':
        c.card.expiration_day = 31
        c.card.save()
        row.account.card = c.card
    with pytest.raises(ValidationError):
        payment_due_date(row)


def test_candidate_search_handles_missing_mapping_and_dates_without_discarding_data(card_source):
    from bank_sync.services import candidates

    c = card_source
    row = c.ingest()
    assert not candidates(row).exists()
    row = c.mapped()
    row.facts.update(bill_id='', date='', purchase_date='')
    assert not candidates(row).exists()


@pytest.mark.parametrize(
    'case', ['invalid_id', 'wrong_number', 'invalid_action', 'unknown_type', 'zero_amount', 'project_single']
)
def test_invalid_card_confirmation_does_not_create_financial_rows(card_source, case):
    from statement.models import CardNumber

    c = card_source
    row = c.mapped()
    action = 'create'
    data = c.create_data()
    if case == 'invalid_id':
        action, data = 'link', {'transaction_id': 'invalid'}
    elif case == 'wrong_number':
        item = c.local(paid=2, installments_number=3)
        item.card_number = CardNumber.objects.create(card=c.card, number='5678')
        item.save()
        action, data = 'link', {'transaction_id': item.pk}
    elif case == 'invalid_action':
        action = 'unknown'
    elif case == 'unknown_type':
        row.facts['payment_type'] = 'UNKNOWN'
    elif case == 'zero_amount':
        row.facts['amount'] = '0'
    else:
        row.facts['payment_type'] = 'SINGLE'
        data['project_remaining'] = True
    row.save()
    before = list(Transaction.objects.values())
    with pytest.raises(ValidationError):
        confirm(c.user, row.pk, row.revision, action, data)
    assert list(Transaction.objects.values()) == before


def test_linking_a_parent_card_transaction_assigns_its_confirmed_number(card_source):
    c = card_source
    row = c.mapped()
    target = c.local(paid=2, installments_number=3)
    target.card_number = None
    target.save()
    confirm(c.user, row.pk, row.revision, 'link', {'transaction_id': target.pk})
    target.refresh_from_db()
    assert target.card_number == c.number


@pytest.mark.parametrize('value', ['NaN', 'Infinity', 'invalid', 10**16, None])
def test_card_sync_rejects_unrepresentable_financial_values(value):
    with pytest.raises(ValidationError):
        money(value)


def test_configured_reader_requires_explicit_server_credentials(settings, monkeypatch, mocker, tmp_path):
    settings.BASE_DIR = tmp_path
    for key in ('PLUGGY_CLIENT_ID', 'PLUGGY_CLIENT_SECRET'):
        monkeypatch.delenv(key, raising=False)
    mocker.patch('dotenv.dotenv_values', return_value={})
    with pytest.raises(ValidationError):
        configured_reader()
    monkeypatch.setenv('PLUGGY_CLIENT_ID', 'test-client')
    monkeypatch.setenv('PLUGGY_CLIENT_SECRET', 'test-secret')
    assert configured_reader().credentials == {'clientId': 'test-client', 'clientSecret': 'test-secret'}


def test_card_sync_rejects_a_concurrent_lease(card_source):
    c = card_source
    c.connection.lease_until = timezone.now() + timedelta(minutes=5)
    c.connection.save()
    with pytest.raises(ValidationError):
        sync_connection(c.connection, c.reader())
    assert not SyncRun.objects.exists()


@pytest.mark.parametrize(
    'reason', ['expired', 'no_cards', 'lost_lease', 'foreign_account', 'foreign_bill', 'foreign_transaction']
)
def test_card_collection_rejects_incomplete_or_cross_owner_source_data(card_source, reason):
    c = card_source
    reader = c.reader()
    if reason == 'expired':
        reader.request.return_value = {
            'status': 'UPDATED',
            'executionStatus': 'SUCCESS',
            'consentExpiresAt': '2000-01-01T00:00:00',
        }
    elif reason == 'no_cards':
        reader.numbered.side_effect = [[{**c.account, 'type': 'DEBIT'}]]
    elif reason == 'lost_lease':
        original = reader.transactions.return_value

        def lose_lease(*args):
            BankConnection.objects.filter(pk=c.connection.pk).update(lease_token=uuid4())
            return original

        reader.transactions.side_effect = lose_lease
    else:
        foreign = BankConnection.objects.create(user=c.other, item_id=uuid4())
        account = ExternalAccount.objects.create(
            connection=foreign, external_id=c.account_id if reason == 'foreign_account' else uuid4()
        )
        if reason == 'foreign_bill':
            ExternalBill.objects.create(account=account, external_id=c.bill_id, total=100)
        elif reason == 'foreign_transaction':
            ExternalTransaction.objects.create(account=account, external_id=c.tx_id, facts={})
    before = list(Transaction.objects.values())
    with pytest.raises(ValidationError):
        sync_connection(c.connection, reader)
    assert list(Transaction.objects.values()) == before
    assert SyncRun.objects.get().state == 'failed'


def test_corrected_bill_due_date_marks_confirmed_occurrences_for_review(card_source):
    c = card_source
    row = c.mapped()
    confirm(c.user, row.pk, row.revision, 'create', c.create_data())
    bill = {**c.bill, 'dueDate': '2026-11-15'}
    sync_connection(c.connection, c.reader(bills=[bill]))
    row.refresh_from_db()
    assert row.state == 'conflict'
    assert row.revision == 2
    assert Transaction.objects.count() == 1


@pytest.mark.parametrize(
    'changes',
    [
        {'currency': 'USD'},
        {'status': 'UNKNOWN'},
        {'payment_type': 'INSTALLMENT', 'number': 0},
        {'payment_type': 'INSTALLMENT', 'total': 121},
        {'payment_type': 'INSTALLMENT', 'number': 2.0},
    ],
)
def test_card_confirmation_rejects_incomplete_financial_facts(card_source, changes):
    c = card_source
    row = c.mapped()
    row.facts.update(changes)
    row.save()
    with pytest.raises(ValidationError):
        confirm(c.user, row.pk, row.revision, 'create', c.create_data())
    assert not Transaction.objects.exists()


def test_conflicted_card_occurrence_cannot_be_silently_recreated(card_source):
    c = card_source
    row = c.mapped()
    row = confirm(c.user, row.pk, row.revision, 'create', c.create_data())
    row.state = 'conflict'
    row.save()
    with pytest.raises(ValidationError):
        confirm(c.user, row.pk, row.revision, 'create', c.create_data())


@pytest.mark.parametrize(
    'facts, expected',
    [
        ({'operation': 'PAGAMENTO_FATURA'}, 'card_payment'),
        ({'direction': 'CREDIT', 'description': 'Pagamento recebido'}, 'card_payment'),
        ({'direction': 'CREDIT', 'description': 'Estorno da compra'}, 'refund'),
        ({'direction': 'OTHER'}, 'unknown'),
    ],
)
def test_bank_notification_classification_preserves_payments_and_refunds(facts, expected):
    assert event_kind(facts) == expected


def test_classifier_disabled_or_unavailable_does_not_block_manual_import(card_source, mocker):
    c = card_source
    row = c.mapped()
    assert 'desativado' in classify(c.user, [row])
    AppConfig.objects.update(enable_transaction_classifier=True)
    mocker.patch('bank_sync.reconciliation.TransactionClassifierClient', side_effect=RuntimeError('unavailable'))
    assert 'não respondeu' in classify(c.user, [row])
    assert not Transaction.objects.exists()
