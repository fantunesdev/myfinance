import pytest

from bank_sync.event_import import adopt_bank_trade, can_adopt
from investments.models import InvestmentTransaction as Movement


def test_already_registered_redemption_can_fund_a_purchase_without_repeating_the_sale(registered_bank_trade):
    b = registered_bank_trade
    b.event.refresh_from_db()
    assert b.event.state == 'applied'
    assert b.trade.journal['source_closed'] is False
    assert b.trade.journal['new_movements']
    assert b.trade.investment.asset.symbol == 'BTC'
    assert Movement.objects.filter(investment=b.investment, type='resgate').count() == 1


def test_later_crypto_event_adopts_the_existing_bank_purchase_without_creating_money(registered_bank_trade):
    b = registered_bank_trade
    before = list(Movement.objects.values())
    assert can_adopt(b.crypto_event, b.crypto_source, b.trade)
    assert adopt_bank_trade(b.connection, b.crypto_event, b.crypto_source)
    b.crypto_source.refresh_from_db()
    b.crypto_event.refresh_from_db()
    assert b.crypto_source.investment_id == b.trade.investment_id
    assert b.crypto_event.state == 'linked'
    assert list(Movement.objects.values()) == before


@pytest.mark.parametrize('change', ['currency', 'state', 'revision', 'date', 'amount', 'quantity', 'identity'])
def test_later_event_must_match_the_exact_confirmed_bank_purchase(registered_bank_trade, change):
    b = registered_bank_trade
    if change == 'currency':
        b.crypto_source.facts['currencyCode'] = 'USD'
    elif change == 'state':
        b.trade.state = 'conflict'
    elif change == 'revision':
        b.trade.debit_revision = 2
    elif change == 'date':
        b.crypto_event.facts['date'] = '2026-11-13T00:00:00Z'
    elif change == 'amount':
        b.crypto_event.facts['netAmount'] = 111
    elif change == 'quantity':
        b.crypto_event.facts['quantity'] = '.02'
    else:
        b.crypto_source.facts['name'] = 'Ethereum'
    assert can_adopt(b.crypto_event, b.crypto_source, b.trade) is None
