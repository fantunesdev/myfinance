from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from api.serializers.transaction import TransactionSerializer
from statement.services.core.card import CardService
from statement.views.core.transaction import TransactionView


@pytest.mark.parametrize('payment,closing,start,end', [
    (date(2026, 11, 10), 3, date(2026, 10, 4), date(2026, 11, 3)),
    (date(2027, 1, 10), 3, date(2026, 12, 4), date(2027, 1, 3)),
    (date(2026, 3, 10), 31, date(2026, 3, 1), date(2026, 3, 31)),
    (date(2024, 2, 10), 31, date(2024, 2, 1), date(2024, 2, 29)),
])
def test_billing_cycle_matches_processing_rule(payment, closing, start, end):
    card = SimpleNamespace(closing_day=closing, expiration_day=payment.day, prepaid=False)
    assert CardService.get_billing_cycle(card, payment) == (start, end)
    current = start
    while current <= end:
        assert CardService.set_processing_date(card, current) == payment
        current += timedelta(days=1)
    assert CardService.set_processing_date(card, start - timedelta(days=1)) != payment
    assert CardService.set_processing_date(card, end + timedelta(days=1)) != payment


@pytest.mark.parametrize('relation,prepaid,visible', [
    ('card', False, True), ('number', False, True),
    ('card', True, True), ('card', False, False), ('cash', False, True),
])
def test_chart_metadata_uses_visible_card_and_handles_prepaid(mocker, relation, prepaid, visible):
    card = SimpleNamespace(closing_day=3, expiration_day=10, prepaid=prepaid)
    transaction = SimpleNamespace(
        card_id=1 if relation == 'card' else None, card=card,
        card_number_id=2 if relation == 'number' else None,
        card_number=SimpleNamespace(card=card), payment_date=date(2026, 11, 10),
    )
    serializer = TransactionSerializer()
    mocker.patch.object(serializer, '_visible_ids', side_effect=lambda name: {1, 2} if visible else set())
    expected = {'kind': 'cash'}
    if visible and not prepaid and relation != 'cash':
        expected = {'kind': 'card', 'cycle_start': '2026-10-04', 'cycle_end': '2026-11-03'}
    assert serializer.get_expense_chart(transaction) == expected


def test_dashboard_counts_prepaid_as_cash_and_credit_as_card(mocker):
    mocker.patch('statement.views.core.transaction.SubcategoryService.get_chart_config_values',
                 return_value={'show_in_monthly_cashflow_donut': True})
    mocker.patch('statement.views.core.transaction.FixedExpensesService.get_active_by_date', return_value=[])
    prepaid = SimpleNamespace(prepaid=True)
    credit = SimpleNamespace(prepaid=False)
    transactions = [
        SimpleNamespace(id=index, subcategory_id=1, user=object(), type='saida', fixed=False,
                        card=card, card_number_id=1 if number_card else None,
                        card_number=SimpleNamespace(card=number_card), value=value)
        for index, (card, number_card, value) in enumerate([
            (prepaid, None, 100), (None, prepaid, 50),
            (credit, None, 200), (None, credit, 75), (None, None, 25),
        ])
    ]
    dashboard = TransactionView()._set_dashboard_templatetags(transactions, 2026, 7)['dashboard']
    assert dashboard['cash'] == 175
    assert dashboard['card'] == 275
    assert dashboard['expenses'] == 450
