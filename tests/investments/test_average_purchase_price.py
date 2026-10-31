from datetime import date
from decimal import Decimal

from django.test import TestCase

from investments.models import Asset, Broker, Investment, InvestmentTransaction
from investments.services.dashboard import dashboard_payload
from investments.services.investment import InvestmentService
from investments.views.investment import InvestmentView
from login.models import User


class AveragePurchasePriceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='average-price', email='average-price@test.invalid'
        )
        self.asset = Asset.objects.create(
            description='Ação', asset_type='variable_income', user=self.user
        )
        broker = Broker.objects.create(description='Broker', user=self.user)
        self.investment = Investment.objects.create(
            description='Posição',
            asset=self.asset,
            broker=broker,
            start_date=date(2026, 1, 1),
            user=self.user,
        )

    def record(self, amount, quantity=None, type='aporte', **fields):
        return InvestmentTransaction.objects.create(
            investment=self.investment,
            user=self.user,
            date=date(2026, 1, 1),
            type=type,
            amount=Decimal(str(amount)),
            quantity=Decimal(str(quantity)) if quantity is not None else None,
            **fields,
        )

    def average(self):
        return InvestmentService.get_average_purchase_price(self.investment)

    def test_purchases_are_weighted_by_quantity_and_use_actual_amount_paid(
        self,
    ):
        self.record(1000, 100, unit_price=Decimal('9.99'))
        self.record(1000, 50)
        self.assertEqual(self.average(), Decimal('2000') / Decimal('150'))

    def test_sale_preserves_average_then_next_purchase_uses_remaining_units(
        self,
    ):
        self.record(1000, 100)
        self.record(800, 40, type='resgate')
        self.assertEqual(self.average(), Decimal('10'))
        self.record(2000, 40)
        self.assertEqual(self.average(), Decimal('26'))

    def test_valuation_income_and_generic_taxes_do_not_change_purchase_price(
        self,
    ):
        self.record(1000, 100)
        self.record(50, type='rendimento')
        self.record(10, type='custo')
        self.record(0, type='atualizacao', current_value=Decimal('1800'))
        self.assertEqual(self.average(), Decimal('10'))

    def test_empty_or_closed_position_has_no_price_and_repurchase_starts_new_average(
        self,
    ):
        self.assertIsNone(self.average())
        self.record(1000, 100)
        self.record(1500, 100, type='resgate')
        self.assertIsNone(self.average())
        self.record(1200, 20)
        self.assertEqual(self.average(), Decimal('60'))

    def test_missing_or_invalid_trade_quantities_make_price_unavailable(self):
        for type, quantity in [
            ('aporte', None),
            ('resgate', None),
            ('aporte', 0),
            ('resgate', 101),
        ]:
            with self.subTest(type=type, quantity=quantity):
                self.investment.transactions.all().delete()
                self.record(1000, 100)
                self.record(100, quantity, type=type)
                self.assertIsNone(self.average())

    def test_crypto_supports_fractional_units_and_small_prices(self):
        self.asset.asset_type = 'crypto'
        self.asset.save()
        self.record(100, '0.001')
        self.record(300, '0.003')
        self.assertEqual(self.average(), Decimal('100000'))
        self.investment.transactions.all().delete()
        self.record('0.10', 100000)
        self.assertEqual(self.average(), Decimal('0.000001'))

    def test_trade_order_is_chronological_and_another_users_records_are_excluded(
        self,
    ):
        sale = self.record(800, 40, type='resgate')
        InvestmentTransaction.objects.filter(pk=sale.pk).update(
            date=date(2026, 1, 2)
        )
        self.record(1000, 100)
        other = User.objects.create(
            username='foreign-price', email='foreign-price@test.invalid'
        )
        InvestmentTransaction.objects.create(
            investment=self.investment,
            user=other,
            date=date(2026, 1, 3),
            type='aporte',
            amount=100000,
            quantity=1,
        )
        self.assertEqual(self.average(), Decimal('10'))

    def test_detail_context_exposes_price_without_modifying_records(self):
        self.record(1000, 100)
        view = InvestmentView()
        view._context = 'detail'
        request = type('Request', (), {'user': self.user})()
        before = list(self.investment.transactions.values())
        context = view._add_context_on_templatetags(request, self.investment)
        self.assertEqual(context['average_purchase_price'], Decimal('10'))
        self.assertEqual(before, list(self.investment.transactions.values()))
        self.asset.asset_type = 'fixed_income'
        self.asset.save()
        self.assertIsNone(self.average())

    def test_dashboard_price_matches_detail_and_is_null_when_not_applicable(
        self,
    ):
        self.record(1000, 100)
        self.record(800, 40, type='resgate')
        self.record(2000, 40)
        record = dashboard_payload(self.user, 'revision')['positions'][0]
        self.assertEqual(
            Decimal(record['average_purchase_price']), self.average()
        )
        self.assertEqual(
            Decimal(record['average_purchase_price']), Decimal('26')
        )
        self.asset.asset_type = 'fixed_income'
        self.asset.save()
        self.assertIsNone(
            dashboard_payload(self.user, 'revision')['positions'][0][
                'average_purchase_price'
            ]
        )

    def test_prefetched_positions_do_not_query_again_to_calculate_average(
        self,
    ):
        self.record(1000, 100)
        cached = (
            Investment.objects.select_related('asset')
            .prefetch_related('transactions')
            .get(pk=self.investment.pk)
        )
        with self.assertNumQueries(0):
            self.assertEqual(
                InvestmentService.get_average_purchase_price(cached),
                Decimal('10'),
            )
