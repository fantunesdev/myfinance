from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from bank_sync.auto_reconciliation import (
    amount,
    bank_proposal,
    event_proposal,
    family,
    matching_cash,
    operation_rows,
    text,
)
from bank_sync.bank_trades import complete, positive, receipt
from bank_sync.cash_reviews import candidates, review_cash
from bank_sync.investment_events import classify, event_date, reconcile
from bank_sync.investments import normalize, ready
from bank_sync.models import InvestmentCashReview
from clients.pluggy.reader import ProbeError
from investments.models import InvestmentTransaction


@pytest.mark.parametrize('value', [None, '', 'invalid', 'NaN', 'Infinity', -1, 0])
def test_invalid_money_cannot_be_used_for_automatic_reconciliation(value):
    assert amount(value) is None
    with pytest.raises(ValidationError):
        positive(value)


def test_positive_amount_and_asset_family_normalization():
    assert amount('12.50') == positive('12.50') == Decimal('12.50')
    assert text('Aplicação LCI') == 'aplicacao lci'
    assert family('Resgate - CDB / LCI') == {'cdb', 'lci'}


@pytest.mark.parametrize(
    'kind, expected',
    [
        ('BUY', 'buy'),
        ('SELL', 'sell'),
        ('INTEREST', 'income'),
        ('TAX', 'tax'),
        ('TRANSFER', 'transfer'),
        ('AMORTIZATION', 'amortization'),
        ('UNKNOWN', 'ambiguous'),
    ],
)
def test_event_classification_preserves_financial_operation_types(kind, expected):
    assert classify({'type': kind, 'quantity': 10}) == (expected, '')


def test_redemption_described_as_income_without_quantity_requires_manual_review():
    kind, reason = classify({'type': 'SELL', 'description': 'Rendimento do CDB'})
    assert kind == 'ambiguous' and reason
    assert event_date({'date': '2026-11-10T00:00:00Z', 'tradeDate': '2026-11-12T00:00:00Z'}) == date(2026, 11, 12)
    with pytest.raises(ValidationError):
        event_date({})


@pytest.mark.parametrize(
    'changes',
    [
        {'status': 'LOGIN_ERROR'},
        {'executionStatus': 'PARTIAL_SUCCESS'},
        {'consentExpiresAt': '2000-01-01T00:00:00Z'},
        {'statusDetail': {'investments': {'error': 'failed'}}},
    ],
)
def test_partial_expired_or_failed_investment_collection_is_rejected(changes):
    with pytest.raises(ProbeError):
        ready({'status': 'UPDATED', 'executionStatus': 'SUCCESS', **changes})


@pytest.mark.parametrize(
    'changes',
    [
        {'id': 'invalid'},
        {'balance': '-1'},
        {'quantity': 'NaN'},
        {'balance': '1000000000000'},
        {'date': '2026-11-12T12:00:00'},
        {'date': 'invalid'},
        {'status': 'TOTAL_WITHDRAWAL', 'balance': '1'},
    ],
)
def test_invalid_position_preserves_the_previous_portfolio(changes):
    from uuid import uuid4

    row = {
        'id': str(uuid4()),
        'balance': '100',
        'quantity': '10',
        'status': 'ACTIVE',
        'date': '2026-11-12T12:00:00Z',
        **changes,
    }
    with pytest.raises(ProbeError):
        normalize(row)


@pytest.mark.parametrize('change', ['no_pair', 'amount', 'date', 'direction', 'unrelated'])
def test_automatic_operation_grouping_requires_a_balanced_wallet_pair(bank_case, change):
    b = bank_case
    if change == 'no_pair':
        b.counterpart.delete()
    elif change == 'amount':
        b.counterpart.amount = 99
        b.counterpart.save()
    elif change == 'date':
        b.counterpart.date += timedelta(days=1)
        b.counterpart.save()
    elif change == 'direction':
        b.counterpart.type = 'resgate'
        b.counterpart.save()
    else:
        b.counterpart.investment = b.investment
        b.counterpart.save()
    assert operation_rows(b.user, b.movement, require_pair=True) is None


def test_legacy_operation_without_a_group_can_only_be_used_when_a_pair_is_optional(bank_case):
    b = bank_case
    b.movement.operation_id = None
    b.movement.save()
    assert operation_rows(b.user, b.movement) == [b.movement]
    assert operation_rows(b.user, b.movement, require_pair=True) is None


@pytest.mark.parametrize('changes', [{'netAmount': None}, {'amount': 99}, {'type': 'TAX'}, {'priceFactor': 100}])
def test_uncertain_events_are_never_automatically_proposed(bank_case, changes):
    b = bank_case
    b.event.facts.update(changes)
    b.event.save()
    before = list(InvestmentTransaction.objects.values())
    assert event_proposal(b.connection, b.event) is None
    assert list(InvestmentTransaction.objects.values()) == before


@pytest.mark.parametrize(
    'changes',
    [
        {'description': 'Resgate - CDB'},
        {'description': 'Transferência LCI'},
        {'amount': 99},
        {'date': '2026-11-13T00:00:00Z'},
    ],
)
def test_unrelated_bank_cash_is_not_matched_to_the_event(bank_case, changes):
    b = bank_case
    b.cash.facts.update(changes)
    b.cash.save()
    assert matching_cash(b.connection, b.event, b.source) == []


@pytest.mark.parametrize('state', ['conflict', 'ignored', 'applied'])
def test_nonpending_events_cannot_be_automatically_proposed(bank_case, state):
    b = bank_case
    b.event.state = state
    b.event.save()
    assert event_proposal(b.connection, b.event) is None


def test_revised_events_and_receipts_require_manual_review(bank_case):
    b = bank_case
    b.event.revision = b.cash.revision = 2
    b.event.save()
    b.cash.save()
    assert event_proposal(b.connection, b.event) is None
    assert matching_cash(b.connection, b.event, b.source) == []
    assert bank_proposal(b.connection, b.cash) is None


@pytest.mark.parametrize('value', ['invalid', 'NaN', 0, -100])
def test_cash_candidates_reject_invalid_amounts_or_direction(bank_case, value):
    b = bank_case
    b.cash.facts['amount'] = value
    with pytest.raises(ValidationError):
        candidates(b.user, b.cash)


def test_cash_candidates_reject_missing_amount(bank_case):
    b = bank_case
    b.cash.facts.pop('amount')
    with pytest.raises(ValidationError):
        candidates(b.user, b.cash)


@pytest.mark.parametrize('evidence', ['', '   ', None, 10])
def test_cash_review_requires_a_written_reason(bank_case, evidence):
    b = bank_case
    with pytest.raises(ValidationError):
        review_cash(b.user, b.cash.pk, b.cash.revision, 'covered', evidence=evidence)
    assert not InvestmentCashReview.objects.exists()


def test_cash_review_rejects_unknown_action(bank_case):
    b = bank_case
    with pytest.raises(ValidationError):
        review_cash(b.user, b.cash.pk, b.cash.revision, 'invalid', evidence='Reviewed')


@pytest.mark.parametrize('changes', [{'status': 'PENDING'}, {'currencyCode': 'USD'}, {'type': 'DEBIT'}])
def test_unsettled_or_wrong_currency_receipts_cannot_fund_a_trade(bank_case, changes):
    b = bank_case
    b.cash.facts.update(changes)
    with pytest.raises(ValidationError):
        receipt(b.cash, 'CREDIT')


def test_trade_requires_a_successful_collection_without_an_active_lease(bank_case):
    b = bank_case
    b.job.state = 'running'
    b.job.save()
    with pytest.raises(ValidationError):
        complete(b.connection)
    b.job.state = 'succeeded'
    b.job.save()
    b.connection.lease_until = timezone.now() + timedelta(minutes=5)
    with pytest.raises(ValidationError):
        complete(b.connection)


@pytest.mark.parametrize('action, evidence', [('keep', ''), ('ignore', ''), ('invalid', 'reviewed')])
def test_invalid_event_review_does_not_modify_money(bank_case, action, evidence):
    b = bank_case
    before = list(InvestmentTransaction.objects.values())
    with pytest.raises(ValidationError):
        reconcile(b.user, b.event.pk, b.event.revision, action, evidence=evidence)
    assert list(InvestmentTransaction.objects.values()) == before


def test_conflicted_unapplied_event_can_be_kept_as_ignored_with_evidence(bank_case):
    b = bank_case
    b.event.state = 'conflict'
    b.event.save()
    assert reconcile(b.user, b.event.pk, b.event.revision, 'keep', evidence='Já conferido') is None
    b.event.refresh_from_db()
    assert b.event.state == 'ignored'
    assert b.event.reason == 'Já conferido'
