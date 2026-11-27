from datetime import date

import pytest
import test_bank_trades as scenarios
from django.core.exceptions import ValidationError

from bank_sync.bank_trades import purchase_options, register_purchase, source_plan
from investments.models import InvestmentTransaction as Movement


@pytest.fixture
def trade_case(db):
    case = scenarios.BankTradeTests()
    case.setUp()
    return case


@pytest.mark.parametrize(
    'invalid',
    [
        'family',
        'history',
        'purchase_revision',
        'purchase_date',
        'opening_rows',
        'purchase_cash',
        'opening_date',
        'opening_counterpart',
        'sale_state',
        'sale_expenses',
        'sale_cash',
        'sale_pair',
        'sale_principal',
        'no_remaining_units',
        'missing_previous_position',
        'extra_transaction',
        'manual_valuation',
        'missing_closing',
    ],
)
def test_source_reconstruction_requires_a_complete_documented_chain(trade_case, invalid):
    c = trade_case
    if invalid == 'family':
        c.credit.facts['description'] = 'Resgate - LCI'
        c.credit.save()
    elif invalid == 'history':
        c.event('INTEREST', '2026-11-09T00:00:00Z', 1, 1, 1)
    elif invalid == 'purchase_revision':
        c.buy.revision = 2
        c.buy.save()
    elif invalid == 'purchase_date':
        c.source.facts['purchaseDate'] = '2026-11-07T00:00:00Z'
        c.source.save()
    elif invalid == 'opening_rows':
        c.buy_op.movements.clear()
    elif invalid == 'purchase_cash':
        c.buy_cash.facts['status'] = 'PENDING'
        c.buy_cash.save()
    elif invalid == 'opening_date':
        c.opening.date = date(2026, 11, 10)
        c.opening.save()
    elif invalid == 'opening_counterpart':
        c.old_debit.amount = 999
        c.old_debit.save()
    elif invalid == 'sale_state':
        c.partial.state = 'new'
        c.partial.save()
    elif invalid == 'sale_expenses':
        c.partial.facts['expenses'] = {'incomeTax': 0}
        c.partial.save()
    elif invalid == 'sale_cash':
        c.partial_cash.facts['status'] = 'PENDING'
        c.partial_cash.save()
    elif invalid == 'sale_pair':
        c.partial_op.movements.remove(c.old_sale)
    elif invalid == 'sale_principal':
        c.old_sale.redemption_principal = 399
        c.old_sale.save()
    elif invalid == 'no_remaining_units':
        c.partial.facts['quantity'] = 1000
        c.partial.save()
    elif invalid == 'missing_previous_position':
        c.source.snapshots.filter(reference_at__date__lt=date(2026, 11, 16)).delete()
    elif invalid == 'extra_transaction':
        Movement.objects.create(user=c.user, investment=c.source_inv, type='custo', amount=1, date=date(2026, 11, 12))
    elif invalid == 'manual_valuation':
        c.plain.current_value = 999
        c.plain.save()
    else:
        quote = c.closing.movement
        c.closing.delete()
        quote.delete()
    before = list(Movement.objects.values())
    with pytest.raises(ValidationError):
        source_plan(c.source, c.credit)
    assert list(Movement.objects.values()) == before
    assert purchase_options(c.debit) == []


@pytest.mark.parametrize('quantity', ['0', '0.000000001', '1000000000000'])
def test_bank_purchase_requires_a_bounded_positive_quantity(trade_case, quantity):
    c = trade_case
    with pytest.raises(ValidationError):
        register_purchase(c.user, c.debit.pk, 1, c.source.pk, c.credit.pk, 'BTC', quantity, 'Documentado')


@pytest.mark.parametrize('symbol', [None, 123, '!', 'A', 'A' * 13])
def test_bank_purchase_requires_an_explicit_valid_asset_symbol(trade_case, symbol):
    c = trade_case
    with pytest.raises(ValidationError):
        register_purchase(c.user, c.debit.pk, 1, c.source.pk, c.credit.pk, symbol, '.01', 'Documentado')


def test_bank_purchase_rejects_an_outdated_receipt_revision(trade_case):
    c = trade_case
    with pytest.raises(ValidationError):
        register_purchase(c.user, c.debit.pk, 2, c.source.pk, c.credit.pk, 'BTC', '.01', 'Documentado')


def test_repeated_bank_purchase_with_different_confirmation_requires_review(trade_case):
    c = trade_case
    trade = register_purchase(c.user, c.debit.pk, 1, c.source.pk, c.credit.pk, 'BTC', '.01', 'Documentado')
    before = list(Movement.objects.values())
    with pytest.raises(ValidationError):
        register_purchase(c.user, c.debit.pk, 1, c.source.pk, c.credit.pk, 'BTC', '.02', 'Documentado')
    assert list(Movement.objects.values()) == before
    assert trade.pk


def test_final_redemption_event_must_be_unprocessed_and_match_the_receipt(trade_case):
    c = trade_case
    c.event('SELL', '2026-11-16T00:00:00Z', 600, 607, 606, {'incomeTax': 1})
    with pytest.raises(ValidationError):
        source_plan(c.source, c.credit)


@pytest.mark.parametrize('invalid', ['duplicate_assets', 'duplicate_positions', 'existing_purchase'])
def test_bank_purchase_rejects_ambiguous_or_already_recorded_crypto_positions(trade_case, invalid):
    from investments.models import Asset, Investment

    c = trade_case
    asset = Asset.objects.create(
        user=c.user, description='Bitcoin BRL', symbol='BTC', asset_type='crypto', currency='BRL'
    )
    if invalid == 'duplicate_assets':
        Asset.objects.create(
            user=c.user, description='Outro Bitcoin BRL', symbol='BTC', asset_type='crypto', currency='BRL'
        )
    else:
        target = Investment.objects.create(
            user=c.user, asset=asset, broker=c.source_inv.broker, description='BTC A', start_date=date(2020, 1, 1)
        )
        if invalid == 'duplicate_positions':
            Investment.objects.create(
                user=c.user, asset=asset, broker=c.source_inv.broker, description='BTC B', start_date=date(2020, 1, 1)
            )
        else:
            Movement.objects.create(
                user=c.user, investment=target, date=date(2026, 11, 16), type='aporte', amount=606, quantity='.01'
            )
    before = list(Movement.objects.values())
    with pytest.raises(ValidationError):
        register_purchase(c.user, c.debit.pk, 1, c.source.pk, c.credit.pk, 'BTC', '.01', 'Conferido')
    assert list(Movement.objects.values()) == before


@pytest.mark.parametrize('changed_position', ['wallet', 'unrelated'])
def test_bank_purchase_rolls_back_if_position_conservation_detects_an_inconsistency(
    trade_case, mocker, changed_position
):
    from investments.services.investment import InvestmentService

    c = trade_case
    original = InvestmentService.get_positions
    calls = 0

    def inconsistent(user):
        nonlocal calls
        positions = original(user)
        calls += 1
        if calls == 2:
            pk = c.wallet.pk if changed_position == 'wallet' else c.old_btc.pk
            for position in positions:
                if position['investment'].pk == pk:
                    position['value'] += 1
        return positions

    mocker.patch.object(InvestmentService, 'get_positions', side_effect=inconsistent)
    before = list(Movement.objects.values())
    with pytest.raises(ValidationError):
        register_purchase(c.user, c.debit.pk, 1, c.source.pk, c.credit.pk, 'BTC', '.01', 'Conferido')
    assert list(Movement.objects.values()) == before


def test_bank_purchase_rolls_back_if_the_source_cost_does_not_close(trade_case, mocker):
    from investments.services.investment import InvestmentService

    c = trade_case
    original = InvestmentService.get_position

    def inconsistent(investment, *args, **kwargs):
        result = original(investment, *args, **kwargs)
        if investment.pk == c.source_inv.pk and result['remaining_principal'] == 0:
            result['remaining_principal'] = 1
        return result

    mocker.patch.object(InvestmentService, 'get_position', side_effect=inconsistent)
    before = list(Movement.objects.values())
    with pytest.raises(ValidationError):
        register_purchase(c.user, c.debit.pk, 1, c.source.pk, c.credit.pk, 'BTC', '.01', 'Conferido')
    assert list(Movement.objects.values()) == before
