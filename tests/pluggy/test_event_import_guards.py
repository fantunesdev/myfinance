from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError

from bank_sync.event_import import bootstrap, funding, import_events, income_cash
from bank_sync.models import ExternalInvestment, InvestmentEvent, InvestmentReconciliationBaseline
from investments.models import Asset
from investments.models import InvestmentTransaction as Movement


@pytest.fixture
def new_title(bank_case):
    b = bank_case
    b.new_source = ExternalInvestment.objects.create(
        connection=b.connection,
        external_id=uuid4(),
        facts={
            'name': 'LCI Nova',
            'type': 'FIXED_INCOME',
            'status': 'ACTIVE',
            'currencyCode': 'BRL',
            'quantity': '10',
            'balance': '100',
            'date': '2026-11-20T12:00:00Z',
            'purchaseDate': '2026-11-12T00:00:00Z',
            'dueDate': '2027-11-12T00:00:00Z',
        },
    )
    b.new_event = InvestmentEvent.objects.create(
        connection=b.connection,
        external_id=str(uuid4()),
        last_seen_job=b.job,
        facts={
            'type': 'BUY',
            'date': '2026-11-12T00:00:00Z',
            'amount': '100',
            'netAmount': '100',
            'quantity': '10',
        },
    )
    b.new_event.investments.add(b.new_source)
    return b


@pytest.mark.parametrize(
    'changes',
    [
        {'type': 'UNKNOWN'},
        {'currencyCode': 'USD'},
        {'status': 'INACTIVE'},
        {'quantity': '20'},
        {'purchaseDate': ''},
        {'purchaseDate': '2026-11-11T00:00:00Z'},
        {'date': '2026-11-10T00:00:00Z'},
        {'name': ''},
        {'name': 'A' * 121},
        {'dueDate': '2027-13-30T00:00:00Z'},
    ],
)
def test_new_title_requires_complete_consistent_source_facts(new_title, changes):
    b = new_title
    b.new_source.facts.update(changes)
    b.new_source.save()
    with pytest.raises(ValidationError):
        bootstrap(b.connection, b.new_source, b.new_event)
    b.new_source.refresh_from_db()
    assert b.new_source.investment_id is None


def test_new_title_cannot_precede_the_reconciled_opening(new_title):
    b = new_title
    InvestmentReconciliationBaseline.objects.create(
        investment=b.investment, date=date(2026, 11, 13), evidence='Abertura'
    )
    with pytest.raises(ValidationError, match='abertura'):
        bootstrap(b.connection, b.new_source, b.new_event)


def test_new_title_requires_an_unambiguous_broker(new_title):
    b = new_title
    b.source.delete()
    with pytest.raises(ValidationError, match='instituição'):
        bootstrap(b.connection, b.new_source, b.new_event)


def test_new_title_cannot_reuse_an_asset_with_another_classification(new_title):
    b = new_title
    Asset.objects.create(user=b.user, description='LCI Nova', symbol='', asset_type='crypto')
    with pytest.raises(ValidationError, match='classificação'):
        bootstrap(b.connection, b.new_source, b.new_event)


def test_new_title_bootstrap_creates_the_matching_fixed_income_asset(new_title):
    b = new_title
    facts, reference = bootstrap(b.connection, b.new_source, b.new_event)
    b.new_source.refresh_from_db()
    assert b.new_source.investment.user == b.user
    assert b.new_source.investment.broker == b.broker
    assert b.new_source.investment.due_date == date(2027, 11, 12)
    assert facts['balance'] == '100'
    assert reference.date() == date(2026, 11, 20)


def test_funding_prefers_a_unique_exact_credit_and_rejects_ambiguous_credit(bank_case):
    b = bank_case
    assert funding(b.user, Decimal(100), date(2026, 11, 12)) == [{'credit_id': b.counterpart.pk, 'amount': '100'}]
    Movement.objects.create(user=b.user, investment=b.wallet, type='aporte', amount=100, date=date(2026, 11, 12))
    with pytest.raises(ValidationError):
        funding(b.user, Decimal(100), date(2026, 11, 12))


def test_income_cash_ignores_unrelated_bank_evidence(bank_case):
    b = bank_case
    b.event.facts.update(type='INTEREST')
    b.event.save()
    assert income_cash(b.connection, b.event) == []


def test_event_import_requires_a_completed_collection(bank_case):
    b = bank_case
    b.job.state = 'running'
    b.job.save()
    with pytest.raises(ValidationError):
        import_events(b.connection)
