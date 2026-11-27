from datetime import date
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from bank_sync.investment_events import reconcile, reconcile_purchase_group, reconcile_transfer_group
from bank_sync.models import (
    ExternalInvestment,
    InvestmentEvent,
    InvestmentSnapshot,
    ReconciledInvestmentOperation,
)
from investments.models import Investment
from investments.models import InvestmentTransaction as Movement


@pytest.fixture
def position(bank_case):
    b = bank_case
    Movement.objects.create(
        user=b.user, investment=b.investment, type='aporte', amount=1000, quantity=100, date=date(2020, 1, 1)
    )
    return b


@pytest.mark.parametrize(
    'changes',
    [
        {'priceFactor': 100},
        {'netAmount': None},
        {'amount': None},
        {'netAmount': 0},
        {'quantity': 0},
        {'quantity': 1000},
        {'amount': 99},
    ],
)
def test_incomplete_or_inconsistent_sale_is_rejected_atomically(position, changes):
    b = position
    b.event.facts.update(changes)
    b.event.save()
    before = list(Movement.objects.values())
    with pytest.raises(ValidationError):
        reconcile(b.user, b.event.pk, 1, 'apply', principal=100, cash_ids=[b.cash.pk], evidence='Liquidação confirmada')
    assert list(Movement.objects.values()) == before
    assert not ReconciledInvestmentOperation.objects.exists()


@pytest.mark.parametrize(
    'changes',
    [
        {'currencyCode': 'USD'},
        {'status': 'PENDING'},
        {'date': '2026-10-01T00:00:00Z'},
        {'amount': 99},
        {'type': 'DEBIT'},
    ],
)
def test_sale_requires_matching_settled_bank_evidence(position, changes):
    b = position
    b.cash.facts.update(changes)
    b.cash.save()
    before = list(Movement.objects.values())
    with pytest.raises(ValidationError):
        reconcile(b.user, b.event.pk, 1, 'apply', principal=100, cash_ids=[b.cash.pk], evidence='Liquidação confirmada')
    assert list(Movement.objects.values()) == before


@pytest.mark.parametrize('missing', ['cash', 'evidence', 'principal'])
def test_sale_requires_cash_documentation_and_known_principal(position, missing):
    b = position
    kwargs = {'cash_ids': [b.cash.pk], 'evidence': 'Liquidação confirmada', 'principal': 100}
    kwargs[{'cash': 'cash_ids', 'evidence': 'evidence', 'principal': 'principal'}[missing]] = {
        'cash': [],
        'evidence': '',
        'principal': None,
    }[missing]
    with pytest.raises(ValidationError):
        reconcile(b.user, b.event.pk, 1, 'apply', **kwargs)


@pytest.mark.parametrize('kind', ['TRANSFER', 'UNKNOWN'])
def test_events_without_an_unambiguous_individual_operation_cannot_be_applied(position, kind):
    b = position
    b.event.facts['type'] = kind
    b.event.save()
    with pytest.raises(ValidationError):
        reconcile(b.user, b.event.pk, 1, 'apply', cash_ids=[b.cash.pk], principal=100, evidence='Reviewed')


def test_foreign_currency_position_cannot_be_reconciled_as_brl(position):
    b = position
    b.asset.currency = 'USD'
    b.asset.save()
    with pytest.raises(ValidationError):
        reconcile(b.user, b.event.pk, 1, 'apply', cash_ids=[b.cash.pk], principal=100, evidence='Reviewed')


@pytest.mark.parametrize('kind, gross, net', [('AMORTIZATION', 100, 99), ('INTEREST', 100, 99), ('SELL', 100, 99)])
def test_supported_cash_in_events_record_operations_with_documented_costs(position, kind, gross, net):
    b = position
    b.event.facts.update(type=kind, amount=gross, netAmount=net)
    b.event.save()
    b.cash.facts['amount'] = net
    b.cash.save()
    op = reconcile(b.user, b.event.pk, 1, 'apply', cash_ids=[b.cash.pk], principal=100, evidence='Liquidação conferida')
    b.event.refresh_from_db()
    assert b.event.state == 'applied'
    assert op.cash_evidence.get() == b.cash
    assert op.movements.filter(investment=b.wallet, type='aporte', amount=net).exists()


@pytest.fixture
def purchases(position):
    b = position
    b.event.facts.update(type='BUY', amount=50, netAmount=50, quantity=5)
    b.event.save()
    b.second = InvestmentEvent.objects.create(
        connection=b.connection, external_id=str(uuid4()), last_seen_job=b.job, facts={**b.event.facts}
    )
    b.second.investments.add(b.source)
    b.cash.facts.update(type='DEBIT', amount=-100)
    b.cash.save()
    b.selections = [{'id': b.event.pk, 'revision': 1}, {'id': b.second.pk, 'revision': 1}]
    b.allocations = [{'credit_id': b.counterpart.pk, 'amount': '100'}]
    return b


@pytest.mark.parametrize(
    'invalid',
    [
        'revision',
        'state',
        'job',
        'source',
        'kind',
        'duplicate',
        'date',
        'cash',
        'fee',
        'evidence',
        'total',
        'quantity',
        'currency',
        'individual_cost',
    ],
)
def test_grouped_purchase_validation_rolls_back_all_changes(purchases, invalid):
    b = purchases
    selections, cash_ids, fee, evidence = b.selections, [b.cash.pk], '0', 'Nota conferida'
    if invalid == 'revision':
        selections[1]['revision'] = 2
    elif invalid == 'state':
        b.second.state = 'historical'
    elif invalid == 'job':
        b.job.state = 'running'
        b.job.save()
    elif invalid == 'source':
        b.second.investments.clear()
    elif invalid == 'kind':
        b.second.facts['type'] = 'SELL'
    elif invalid == 'duplicate':
        selections[1] = selections[0]
    elif invalid == 'date':
        b.second.facts['date'] = '2026-11-13T00:00:00Z'
    elif invalid == 'cash':
        cash_ids = []
    elif invalid == 'fee':
        fee = '-1'
    elif invalid == 'evidence':
        evidence = ''
    elif invalid == 'total':
        b.second.facts['netAmount'] = 49
    elif invalid == 'quantity':
        b.second.facts['quantity'] = 0
    elif invalid == 'currency':
        b.asset.currency = 'USD'
        b.asset.save()
    else:
        b.second.facts['amount'] = 51
    b.second.save()
    before = list(Movement.objects.values())
    with pytest.raises(ValidationError):
        reconcile_purchase_group(b.user, selections, cash_ids, b.allocations, fee, evidence)
    assert list(Movement.objects.values()) == before
    assert not ReconciledInvestmentOperation.objects.exists()


@pytest.fixture
def transfer(position):
    b = position
    b.destination = Investment.objects.create(
        user=b.user, asset=b.asset, broker=b.broker, description='Destino', start_date=date(2020, 1, 1)
    )
    b.target = ExternalInvestment.objects.create(connection=b.connection, external_id=uuid4(), investment=b.destination)
    b.event.facts.update(type='TRANSFER', movementType='DEBIT')
    b.event.save()
    b.second = InvestmentEvent.objects.create(
        connection=b.connection,
        external_id=str(uuid4()),
        last_seen_job=b.job,
        facts={**b.event.facts, 'movementType': 'CREDIT'},
    )
    b.second.investments.add(b.target)
    b.selections = [{'id': b.event.pk, 'revision': 1}, {'id': b.second.pk, 'revision': 1}]
    return b


@pytest.mark.parametrize(
    'invalid',
    ['count', 'evidence', 'revision', 'state', 'source', 'direction', 'destination', 'date', 'quantity', 'position'],
)
def test_transfer_validation_never_modifies_partial_legs(transfer, invalid):
    b = transfer
    selections, evidence = b.selections, 'Transferência conferida'
    if invalid == 'count':
        selections = selections[:1]
    elif invalid == 'evidence':
        evidence = ''
    elif invalid == 'revision':
        selections[1]['revision'] = 2
    elif invalid == 'state':
        b.second.state = 'historical'
    elif invalid == 'source':
        b.second.investments.clear()
    elif invalid == 'direction':
        b.second.facts['movementType'] = 'DEBIT'
    elif invalid == 'destination':
        b.second.investments.set([b.source])
    elif invalid == 'date':
        b.second.facts['date'] = '2026-11-13T00:00:00Z'
    elif invalid == 'quantity':
        b.second.facts['quantity'] = 9
    else:
        b.event.facts['quantity'] = b.second.facts['quantity'] = 1000
        b.event.save()
    b.second.save()
    before = list(Movement.objects.values())
    with pytest.raises(ValidationError):
        reconcile_transfer_group(b.user, selections, 100, evidence)
    assert list(Movement.objects.values()) == before


def test_transfer_preserves_later_official_positions_for_both_legs(transfer):
    b = transfer
    reference = timezone.now()
    for ext, value, quantity in [(b.source, 900, 90), (b.target, 100, 10)]:
        quote = Movement.objects.create(
            user=b.user,
            investment=ext.investment,
            date=reference.date(),
            type='atualizacao',
            current_value=value,
            quantity=quantity,
        )
        InvestmentSnapshot.objects.create(
            external=ext,
            reference_at=reference,
            fingerprint=uuid4().hex,
            facts={'balance': str(value), 'quantity': str(quantity)},
            movement=quote,
        )
    op = reconcile_transfer_group(b.user, b.selections, 100, 'Transferência conferida')
    assert op.kind == 'transfer'
    assert op.movements.filter(notes='Posição oficial preservada após transferência conciliada.').count() == 2
