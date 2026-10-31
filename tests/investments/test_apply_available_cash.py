from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from investments.models import Asset, Investment, InvestmentTransaction
from investments.services.investment import InvestmentService
from investments.services.transaction import (
    InvestmentTransactionService as Service,
)
from investments.views.investment import InvestmentView
from login.models import User


@override_settings(ALLOWED_HOSTS=['testserver'])
class ApplyAvailableCashTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='apply-cash', email='apply-cash@test.invalid'
        )
        self.wallet = Service.get_or_create_default_wallet(self.user)
        asset = Asset.objects.create(
            description='CDB', asset_type='fixed_income', user=self.user
        )
        self.destination = Investment.objects.create(
            description='CDB DI',
            asset=asset,
            broker=self.wallet.broker,
            user=self.user,
            start_date=date(2026, 1, 1),
            due_date=date(2027, 1, 1),
        )
        InvestmentTransaction.objects.create(
            investment=self.wallet,
            user=self.user,
            type='aporte',
            date=date(2026, 1, 1),
            amount=1000,
        )

    def request(self, method='get', data=None, user=None):
        request = getattr(RequestFactory(), method)(
            reverse('apply_available_investment_cash'), data=data or {}
        )
        request.user = user or self.user
        return request

    def render_context(self, request):
        with patch.object(
            InvestmentView,
            '_render',
            side_effect=lambda r, form, template, context: {
                'form': form,
                **context,
            },
        ):
            return InvestmentView().apply_available_cash(request)

    def post_data(self, **changes):
        return {
            'asset_type': 'fixed_income',
            'investment': self.destination.pk,
            'date': '2026-01-02',
            'amount': '250',
            **changes,
        }

    def test_get_prefills_cash_and_only_lists_own_active_destinations_without_writes(
        self,
    ):
        closed = Investment.objects.create(
            description='Encerrado',
            asset=self.destination.asset,
            broker=self.wallet.broker,
            user=self.user,
            start_date=date(2026, 1, 1),
            status='closed',
        )
        other = User.objects.create(
            username='foreign-cash', email='foreign-cash@test.invalid'
        )
        foreign = Service.get_or_create_default_wallet(other)
        before = list(InvestmentTransaction.objects.order_by('pk').values())
        context = self.render_context(self.request())
        form = context['form']
        self.assertEqual(form.initial['amount'], Decimal('1000'))
        self.assertIsInstance(form.initial['date'], date)
        self.assertEqual(
            list(
                form.fields['investment'].queryset.values_list('pk', flat=True)
            ),
            [self.destination.pk],
        )
        self.assertEqual(
            context['destination_options'][str(self.destination.pk)],
            {'asset_type': 'fixed_income', 'due_date': '2027-01-01'},
        )
        self.assertEqual(
            before, list(InvestmentTransaction.objects.order_by('pk').values())
        )
        for invalid in [closed.pk, foreign.pk, self.wallet.pk]:
            result = self.render_context(
                self.request('post', self.post_data(investment=invalid))
            )
            self.assertIn('investment', result['form'].errors)
        self.assertEqual(
            before, list(InvestmentTransaction.objects.order_by('pk').values())
        )

    def test_post_transfers_cash_and_ignores_unit_fields_for_fixed_income(
        self,
    ):
        response = InvestmentView().apply_available_cash(
            self.request(
                'post', self.post_data(quantity='2', unit_price='125')
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('investments_dashboard'))
        self.assertEqual(
            InvestmentService.get_position(self.wallet)['value'],
            Decimal('750'),
        )
        self.assertEqual(
            InvestmentService.get_position(self.destination)['value'],
            Decimal('250'),
        )
        credit = self.destination.transactions.get()
        self.assertIsNone(credit.quantity)
        self.assertIsNone(credit.unit_price)
        self.assertEqual(credit.due_date, date(2027, 1, 1))
        self.assertEqual(
            InvestmentTransaction.objects.filter(
                operation_id=credit.operation_id
            ).count(),
            2,
        )

    def test_variable_income_preserves_quantity_and_purchase_price(self):
        self.destination.asset.asset_type = 'variable_income'
        self.destination.asset.save()
        response = InvestmentView().apply_available_cash(
            self.request(
                'post',
                self.post_data(
                    asset_type='variable_income',
                    quantity='2',
                    unit_price='125',
                ),
            )
        )
        self.assertEqual(response.status_code, 302)
        credit = self.destination.transactions.get()
        self.assertEqual(credit.quantity, Decimal('2'))
        self.assertEqual(credit.unit_price, Decimal('125'))

    def test_insufficient_balance_returns_form_error_without_partial_writes(
        self,
    ):
        before = list(InvestmentTransaction.objects.values())
        result = self.render_context(
            self.request('post', self.post_data(amount='1000.01'))
        )
        self.assertIn(
            'Saldo insuficiente', str(result['form'].non_field_errors())
        )
        self.assertEqual(before, list(InvestmentTransaction.objects.values()))

    def test_successful_post_redirects_and_following_get_does_not_repeat_transfer(
        self,
    ):
        response = InvestmentView().apply_available_cash(
            self.request('post', self.post_data())
        )
        self.assertEqual(response.status_code, 302)
        before = list(InvestmentTransaction.objects.order_by('pk').values())
        self.render_context(self.request())
        self.assertEqual(
            before, list(InvestmentTransaction.objects.order_by('pk').values())
        )

    def test_anonymous_request_requires_login(self):
        response = InvestmentView().apply_available_cash(
            self.request(user=AnonymousUser())
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_get_without_default_wallet_does_not_create_one(self):
        other = User.objects.create(
            username='no-cash', email='no-cash@test.invalid'
        )
        with patch('investments.views.investment.messages.warning'):
            response = InvestmentView().apply_available_cash(
                self.request(user=other)
            )
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(Service.get_default_wallet(other))

    def test_type_comes_first_and_mismatched_destination_cannot_be_applied(
        self,
    ):
        crypto_asset = Asset.objects.create(
            description='Bitcoin', asset_type='crypto', user=self.user
        )
        crypto = Investment.objects.create(
            description='BTC',
            asset=crypto_asset,
            broker=self.wallet.broker,
            user=self.user,
            start_date=date(2026, 1, 1),
        )
        context = self.render_context(self.request())
        self.assertEqual(next(iter(context['form'].fields)), 'asset_type')
        self.assertEqual(
            set(
                value
                for value, label in context['form']
                .fields['asset_type']
                .choices
            ),
            {'', 'fixed_income', 'crypto'},
        )
        before = list(InvestmentTransaction.objects.order_by('pk').values())
        result = self.render_context(
            self.request('post', self.post_data(investment=crypto.pk))
        )
        self.assertIn('investment', result['form'].errors)
        data = self.post_data()
        data.pop('asset_type')
        missing = self.render_context(self.request('post', data))
        self.assertIn('asset_type', missing['form'].errors)
        self.assertEqual(
            before, list(InvestmentTransaction.objects.order_by('pk').values())
        )
