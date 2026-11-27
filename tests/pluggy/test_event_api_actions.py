import json
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.test import RequestFactory

from bank_sync import event_views
from bank_sync.models import BankConnection, InvestmentEvent, InvestmentHistoryJob
from investments.models import InvestmentTransaction


def request(user, data=None, method='post'):
    result = getattr(RequestFactory(), method)(
        '/events/', data=json.dumps(data or {}) if method == 'post' else data or {}, content_type='application/json'
    )
    result.user = user
    return result


def test_event_review_can_ignore_with_evidence_and_never_changes_money(bank_case):
    b = bank_case
    before = list(InvestmentTransaction.objects.values())
    response = event_views.review(
        request(b.user, {'revision': 1, 'action': 'ignore', 'evidence': 'Documentado'}), b.event.pk
    )
    assert response.status_code == 200
    assert json.loads(response.content) == {'operation_id': None}
    b.event.refresh_from_db()
    assert b.event.state == 'ignored'
    assert list(InvestmentTransaction.objects.values()) == before


def test_bank_review_can_mark_a_receipt_as_already_covered(bank_case):
    b = bank_case
    response = event_views.bank_review(
        request(b.user, {'revision': 1, 'action': 'covered', 'evidence': 'Incluído na abertura'}), b.cash.pk
    )
    assert response.status_code == 200
    assert json.loads(response.content)['review_id']
    assert b.cash.reviews.get().action == 'covered'


def test_bank_conflict_review_dispatches_the_expected_revision(bank_case, mocker):
    b = bank_case
    keep = mocker.patch('bank_sync.bank_trades.keep_bank_trade', return_value=SimpleNamespace(pk=123))
    response = event_views.bank_review(
        request(b.user, {'revision': 2, 'action': 'keep', 'evidence': 'Conferido'}), b.cash.pk
    )
    assert response.status_code == 200
    keep.assert_called_once_with(b.user, b.cash.pk, 2, 'Conferido')
    assert json.loads(response.content) == {'trade_id': 123}


def test_bank_purchase_dispatches_only_the_explicitly_reviewed_values(bank_case, mocker):
    b = bank_case
    register = mocker.patch(
        'bank_sync.bank_trades.register_purchase',
        return_value=SimpleNamespace(pk=123, investment_id=456, quantity=Decimal('.01'), amount=Decimal(100)),
    )
    data = {
        'revision': 1,
        'source_id': b.source.pk,
        'credit_id': b.cash.pk,
        'symbol': 'BTC',
        'quantity': '.01',
        'evidence': 'Compra documentada',
    }
    response = event_views.bank_purchase(request(b.user, data), b.cash.pk)
    assert response.status_code == 200
    assert json.loads(response.content)['investment_id'] == 456
    register.assert_called_once_with(b.user, b.cash.pk, 1, b.source.pk, b.cash.pk, 'BTC', '.01', 'Compra documentada')


@pytest.mark.parametrize(
    'kind, service', [('TRANSFER', 'reconcile_transfer_group'), ('BUY', 'reconcile_purchase_group')]
)
def test_group_review_dispatches_the_correct_operation(bank_case, mocker, kind, service):
    b = bank_case
    b.event.facts['type'] = kind
    b.event.save()
    other = InvestmentEvent.objects.create(
        connection=b.connection, external_id=str(uuid4()), last_seen_job=b.job, facts={**b.event.facts}
    )
    reconcile = mocker.patch('bank_sync.investment_events.' + service, return_value=SimpleNamespace(pk=123))
    data = {
        'action': 'apply',
        'events': [{'id': b.event.pk, 'revision': 1}, {'id': other.pk, 'revision': 1}],
        'evidence': 'Grupo documentado',
    }
    response = event_views.review(request(b.user, data), b.event.pk)
    assert response.status_code == 200
    assert json.loads(response.content) == {'operation_id': 123}
    assert reconcile.call_args.args[:2] == (b.user, data['events'])


def test_group_review_rejects_actions_which_must_be_individual(bank_case):
    b = bank_case
    response = event_views.review(
        request(b.user, {'action': 'ignore', 'events': [{'id': b.event.pk}, {'id': 99999}]}), b.event.pk
    )
    assert response.status_code == 400


def test_collection_endpoint_queues_once_and_returns_the_existing_job(bank_case):
    b = bank_case
    first = event_views.enqueue(request(b.user))
    second = event_views.enqueue(request(b.user))
    assert first.status_code == second.status_code == 202
    assert json.loads(first.content)['job_id'] == json.loads(second.content)['job_id']
    assert InvestmentHistoryJob.objects.filter(connection=b.connection, state='queued').count() == 1


@pytest.mark.parametrize('view', [event_views.enqueue, event_views.auto_link])
def test_bulk_actions_require_an_unambiguous_connection(bank_case, view):
    b = bank_case
    BankConnection.objects.create(user=b.user, item_id=uuid4())
    assert view(request(b.user)).status_code == 400


def test_auto_link_endpoint_reports_links_without_exposing_financial_payloads(bank_case, mocker):
    b = bank_case
    mocker.patch('bank_sync.auto_reconciliation.auto_reconcile', return_value={'events': [1], 'bank_entries': []})
    mocker.patch('bank_sync.event_import.import_events', return_value={'applied': [1, 2], 'adopted': [3]})
    response = event_views.auto_link(request(b.user))
    assert response.status_code == 200
    assert json.loads(response.content) == {'events': 1, 'bank_entries': 0, 'registered': 2, 'adopted': 1}


def test_event_listing_accepts_individual_state_filters_and_shows_available_funding(bank_case):
    b = bank_case
    b.event.facts.update(type='BUY', netAmount=100, amount=100)
    b.event.save()
    response = event_views.event_list(request(b.user, {'state': 'new'}, method='get'))
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['filter'] == 'new'
    assert data['events'][0]['id'] == b.event.pk
    assert any(credit['id'] == b.counterpart.pk for credit in data['credits'])
