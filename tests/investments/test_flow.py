import importlib
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from api.views.investment import InvestmentTransactionView as APITransactionView
from api.views.investment import InvestmentView as APIInvestmentView
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.forms import model_to_dict
from django.test import RequestFactory, TestCase, TransactionTestCase
from investments.forms.investment import InvestmentCashMovementForm
from investments.forms.transaction import InvestmentTransactionForm
from investments.models import Asset, Investment, InvestmentTransaction
from investments.services.investment import InvestmentService
from investments.services.transaction import InvestmentTransactionService as Service
from investments.views.base import InvestmentCrudView
from investments.views.transaction import InvestmentTransactionView
from login.models import User
from rest_framework.test import APIRequestFactory, force_authenticate
from statement.models import Category, Currency, Subcategory, Transaction
from statement.services.core.transaction import TransactionService


class InvestmentFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='audit', email='audit@example.invalid')
        self.wallet = Service.get_or_create_default_wallet(self.user)
        asset = Asset.objects.create(description='CDB', asset_type='fixed_income', user=self.user)
        self.investment = Investment.objects.create(
            description='Aplicação',
            asset=asset,
            broker=self.wallet.broker,
            start_date=date(2026, 1, 1),
            user=self.user,
        )
        Currency.objects.get_or_create(id='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
        category = Category.objects.create(description='Investimentos', type='saida')
        self.subcategory = Subcategory.objects.create(description='Aportes', category=category, is_investment=True)

    def record(self, investment=None, **kwargs):
        return InvestmentTransaction.objects.create(
            investment=investment or self.investment,
            user=self.user,
            **{'date': date(2026, 1, 1), 'type': 'aporte', 'amount': Decimal('1000'), **kwargs},
        )

    def statement(self, **kwargs):
        return Transaction.objects.create(
            user=self.user,
            category=self.subcategory.category,
            subcategory=self.subcategory,
            **{
                'posted_date': date(2026, 1, 1),
                'payment_date': date(2026, 1, 1),
                'description': 'Aporte',
                'value': 1000,
                'type': 'saida',
                'effected': True,
                **kwargs,
            },
        )

    def value(self, investment=None):
        return InvestmentService.get_position(investment or self.investment)['value']

    def edit(self, instance, **changes):
        data = model_to_dict(instance)
        data.update(changes)
        form = InvestmentTransactionForm(data, instance=instance, user=self.user)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        return Service.update(form, instance)

    def apply(self, amount=1000, funding=None, **kwargs):
        return Service.transfer_between_investments(
            self.wallet,
            self.investment,
            amount,
            date=date(2026, 1, 2),
            funding_transaction=funding,
            **kwargs,
        )

    def test_transfer_conserves_total(self):
        self.record(self.wallet)
        self.apply(600)
        self.assertEqual((self.value(self.wallet), self.value()), (Decimal('400'), Decimal('600')))

    def test_edit_either_transfer_leg_synchronizes_peer(self):
        self.record(self.wallet)
        source, destination = self.apply(600)
        for leg, peer, amount in ((source, destination, '500'), (destination, source, '400')):
            self.edit(leg, amount=amount)
            peer.refresh_from_db()
            self.assertEqual(peer.amount, Decimal(amount))
            self.assertEqual(self.value(self.wallet) + self.value(), Decimal('1000'))

    def test_delete_either_leg_removes_complete_operation(self):
        self.record(self.wallet)
        for index in (0, 1):
            legs = self.apply()
            operation = legs[0].operation_id
            Service.delete(legs[index])
            self.assertFalse(InvestmentTransaction.objects.filter(operation_id=operation).exists())
            self.assertEqual((self.value(self.wallet), self.value()), (Decimal('1000'), Decimal('0')))

    def test_type_change_never_overwrites_original_funding(self):
        statement = self.statement()
        funding = InvestmentTransaction.objects.get(statement_transaction=statement)
        _, destination = self.apply(funding=funding)
        with self.assertRaises(ValidationError):
            self.edit(destination, type='resgate', amount='300')
        funding.refresh_from_db()
        self.assertEqual(funding.amount, Decimal('1000'))
        self.assertIsNone(funding.operation_id)
        Service.delete(destination)
        self.assertTrue(InvestmentTransaction.objects.filter(pk=funding.pk).exists())

    def test_funding_link_is_separate_from_transfer_uuid(self):
        funding = self.record(self.wallet)
        _, destination = self.apply(funding=funding)
        funding.refresh_from_db()
        self.assertIsNone(funding.operation_id)
        self.assertEqual(destination.funding_transaction_id, funding.pk)

    def test_funding_replay_is_rejected_even_with_sufficient_wallet_balance(self):
        funding = self.record(self.wallet)
        self.record(self.wallet)
        self.apply(funding=funding)
        with self.assertRaises(ValidationError):
            self.apply(funding=funding)
        self.assertEqual((self.value(self.wallet), self.value()), (Decimal('1000'), Decimal('1000')))

    def test_funding_can_be_used_again_after_operation_deleted(self):
        funding = self.record(self.wallet)
        _, destination = self.apply(funding=funding)
        Service.delete(destination)
        self.apply(funding=funding)
        self.assertEqual(self.value(), Decimal('1000'))

    def test_funding_amount_and_date_cannot_be_exceeded(self):
        funding = self.record(self.wallet)
        self.record(self.wallet)
        with self.assertRaises(ValidationError):
            self.apply(1100, funding=funding)
        with self.assertRaises(ValidationError):
            Service.transfer_between_investments(
                self.wallet, self.investment, 100, date=date(2025, 12, 31), funding_transaction=funding
            )

    def test_used_funding_cannot_be_reduced_or_deleted(self):
        funding = self.record(self.wallet)
        self.apply(funding=funding)
        with self.assertRaises(ValidationError):
            self.edit(funding, amount='700')
        funding.refresh_from_db()
        with self.assertRaises(ValidationError):
            Service.delete(funding)
        self.assertEqual(funding.amount, Decimal('1000'))

    def test_reducing_funding_without_explicit_reference_still_checks_wallet(self):
        funding = self.record(self.wallet)
        self.apply()
        with self.assertRaises(ValidationError):
            self.edit(funding, amount='500')
        funding.refresh_from_db()
        self.assertEqual(funding.amount, Decimal('1000'))

    def test_investment_with_history_cannot_be_deleted(self):
        self.record(self.wallet)
        self.apply()
        with self.assertRaises(ValidationError):
            InvestmentService.delete(self.investment)
        self.assertTrue(Investment.objects.filter(pk=self.investment.pk).exists())
        self.assertEqual(self.value(), Decimal('1000'))

    def test_empty_investment_can_be_deleted_but_wallet_cannot(self):
        InvestmentService.delete(self.investment)
        with self.assertRaises(ValidationError):
            InvestmentService.delete(self.wallet)

    def test_bulk_parent_deletion_cannot_bypass_history_protection(self):
        self.record()
        with self.assertRaises(ProtectedError):
            Investment.objects.filter(pk=self.investment.pk).delete()
        self.assertEqual(self.value(), Decimal('1000'))

    def test_manual_redemption_keeps_remaining_principal_consistent(self):
        self.record()
        self.record(type='rendimento', amount=100)
        form = InvestmentTransactionForm(
            {
                'investment': self.investment.pk,
                'date': '2026-02-01',
                'type': 'resgate',
                'amount': '550',
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())
        movement = Service.create(form, self.user)
        self.assertEqual(movement.redemption_principal, Decimal('500'))
        self.assertEqual(InvestmentService.get_position(self.investment)['remaining_principal'], Decimal('500'))
        self.assertEqual((self.value(), self.value(self.wallet)), (Decimal('550'), Decimal('550')))

    def test_service_does_not_use_stale_prefetched_balance(self):
        self.record(self.wallet)
        cached = Investment.objects.prefetch_related('transactions').get(pk=self.wallet.pk)
        self.apply()
        with self.assertRaises(ValidationError):
            Service.transfer_between_investments(cached, self.investment, 1000)

    def test_latest_valuation_and_chart_match(self):
        self.record()
        self.record(type='atualizacao', amount=0, current_value=1100, date=date(2026, 2, 1))
        self.record(type='atualizacao', amount=0, current_value=1200, date=date(2026, 3, 1))
        self.assertEqual(self.value(), Decimal('1200'))
        chart = sum(Decimal(str(item['values'][-1])) for item in InvestmentService.get_progression_datasets(self.user))
        self.assertEqual(chart, self.value())

    def test_cashflows_after_valuation_count_with_prefetch(self):
        self.record()
        self.record(type='atualizacao', amount=0, current_value=1100, date=date(2026, 2, 1))
        self.record(amount=500, date=date(2026, 3, 1))
        prefetched = Investment.objects.prefetch_related('transactions').get(pk=self.investment.pk)
        self.assertEqual(InvestmentService.get_position(prefetched)['value'], Decimal('1600'))

    def test_valuation_same_day_uses_id_order(self):
        self.record()
        self.record(type='atualizacao', amount=0, current_value=1100)
        self.record(amount=500)
        self.assertEqual(self.value(), Decimal('1600'))

    def test_redemption_without_prior_income(self):
        self.record()
        Service.redeem_to_wallet(self.investment, 1100, 1000, date=date(2026, 2, 1))
        self.assertEqual((self.value(), self.value(self.wallet)), (Decimal('0'), Decimal('1100')))
        self.assertEqual(InvestmentService.get_dashboard(self.user)['total_income'], Decimal('100'))

    def test_existing_income_is_not_counted_twice(self):
        self.record()
        self.record(type='rendimento', amount=100)
        Service.redeem_to_wallet(self.investment, 1100, 1000, date=date(2026, 2, 1))
        self.assertEqual((self.value(), self.value(self.wallet)), (Decimal('0'), Decimal('1100')))
        self.assertEqual(InvestmentService.get_dashboard(self.user)['total_income'], Decimal('100'))

    def test_valuation_redemption_leaves_no_phantom_position(self):
        self.record()
        self.record(type='atualizacao', amount=0, current_value=1100, date=date(2026, 2, 1))
        Service.redeem_to_wallet(self.investment, 1100, 1000, date=date(2026, 3, 1))
        self.assertEqual((self.value(), self.value(self.wallet)), (Decimal('0'), Decimal('1100')))
        self.assertEqual(InvestmentService.get_dashboard(self.user)['net_income'], Decimal('100'))

    def test_partial_redemptions_allocate_known_income(self):
        self.record()
        self.record(type='rendimento', amount=100)
        for day in (1, 2):
            Service.redeem_to_wallet(self.investment, 550, 500, date=date(2026, 2, day))
        self.assertEqual((self.value(), self.value(self.wallet)), (Decimal('0'), Decimal('1100')))
        self.assertEqual(InvestmentService.get_dashboard(self.user)['total_income'], Decimal('100'))

    def test_partial_redemptions_after_valuation_realize_only_new_gains(self):
        self.record()
        self.record(type='atualizacao', amount=0, current_value=1100, date=date(2026, 2, 1))
        Service.redeem_to_wallet(self.investment, 550, 500, date=date(2026, 3, 1))
        self.assertEqual(self.value(), Decimal('550'))
        Service.redeem_to_wallet(self.investment, 550, 500, date=date(2026, 3, 2))
        self.assertEqual(self.value(), Decimal('0'))
        self.assertEqual(InvestmentService.get_dashboard(self.user)['total_income'], Decimal('100'))

    def test_loss_is_not_counted_twice(self):
        self.record()
        self.record(type='custo', amount=100)
        Service.redeem_to_wallet(self.investment, 900, 1000, date=date(2026, 2, 1))
        self.assertEqual(self.value(), Decimal('0'))
        self.assertEqual(InvestmentService.get_dashboard(self.user)['total_costs'], Decimal('100'))

    def test_delete_redemption_reverts_every_generated_record(self):
        self.record()
        for entry_type in ('resgate', 'aporte', 'rendimento'):
            records = Service.redeem_to_wallet(self.investment, 1100, 1000, date=date(2026, 2, 1))
            selected = next(item for item in records if item.type == entry_type)
            operation_id = selected.operation_id
            Service.delete(selected)
            self.assertFalse(InvestmentTransaction.objects.filter(operation_id=operation_id).exists())
            self.assertEqual((self.value(), self.value(self.wallet)), (Decimal('1000'), Decimal('0')))

    def test_edit_compound_redemption_is_blocked_atomically(self):
        self.record()
        records = Service.redeem_to_wallet(self.investment, 1100, 1000, date=date(2026, 2, 1))
        for item in records:
            with self.assertRaises(ValidationError):
                self.edit(item, amount='1200')
        self.assertEqual((self.value(), self.value(self.wallet)), (Decimal('0'), Decimal('1100')))

    def test_repeated_full_redemption_is_blocked(self):
        self.record()
        Service.redeem_to_wallet(self.investment, 1000, 1000)
        with self.assertRaises(ValidationError):
            Service.redeem_to_wallet(self.investment, 1000, 1000)
        self.assertEqual((self.value(), self.value(self.wallet)), (Decimal('0'), Decimal('1000')))

    def test_wallet_survives_all_display_name_changes(self):
        self.wallet.description = 'Meu caixa'
        self.wallet.save()
        self.wallet.asset.symbol = 'MEU-CASH'
        self.wallet.asset.save()
        self.wallet.broker.description = 'Minha carteira'
        self.wallet.broker.save()
        self.assertEqual(Service.get_or_create_default_wallet(self.user).pk, self.wallet.pk)

    def test_linked_funding_cannot_be_edited_or_deleted_directly(self):
        statement = self.statement()
        funding = InvestmentTransaction.objects.get(statement_transaction=statement)
        with self.assertRaises(ValidationError):
            self.edit(funding, amount='700')
        funding.refresh_from_db()
        with self.assertRaises(ValidationError):
            Service.delete(funding)
        self.assertEqual(self.value(self.wallet), Decimal('1000'))

    def test_zero_statement_rolls_back_source_and_wallet(self):
        statement = self.statement()
        statement.value = 0
        with self.assertRaises(ValidationError):
            statement.save()
        statement.refresh_from_db()
        self.assertEqual(statement.value, 1000)
        self.assertEqual(self.value(self.wallet), Decimal('1000'))

    def test_signal_failure_rolls_back_new_statement(self):
        with patch.object(
            Service, 'sync_wallet_contribution_from_statement_transaction', side_effect=ValidationError('falha')
        ):
            with self.assertRaises(ValidationError):
                self.statement()
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 0)

    def test_used_statement_cannot_be_recategorized_deleted_or_reduced(self):
        statement = self.statement()
        funding = InvestmentTransaction.objects.get(statement_transaction=statement)
        self.apply(funding=funding)
        other = Subcategory.objects.create(description='Outra', category=self.subcategory.category)
        statement.subcategory = other
        with self.assertRaises(ValidationError):
            statement.save()
        statement.refresh_from_db()
        statement.value = 700
        with self.assertRaises(ValidationError):
            statement.save()
        statement.refresh_from_db()
        with self.assertRaises(ValidationError):
            TransactionService.delete(statement)
        self.assertEqual((self.value(self.wallet), self.value()), (Decimal('0'), Decimal('1000')))

    def test_unused_statement_can_be_deleted_and_recategorized(self):
        statement = self.statement()
        TransactionService.delete(statement)
        self.assertEqual(self.value(self.wallet), Decimal('0'))
        statement = self.statement()
        other = Subcategory.objects.create(description='Outra', category=self.subcategory.category)
        statement.subcategory = other
        statement.save()
        self.assertFalse(InvestmentTransaction.objects.filter(statement_transaction=statement).exists())

    def test_effected_behavior_is_unchanged(self):
        statement = self.statement(effected=False, payment_date=date(2027, 1, 1))
        self.assertFalse(statement.effected)
        self.assertEqual(self.value(self.wallet), Decimal('1000'))
        statement.effected = True
        statement.save()
        self.assertEqual(self.value(self.wallet), Decimal('1000'))

    def test_invalid_values_are_form_errors(self):
        for amount in ('-100', '0'):
            form = InvestmentCashMovementForm({'date': '2026-01-01', 'amount': amount}, investment=self.investment)
            self.assertFalse(form.is_valid())
            form = InvestmentTransactionForm(
                {'investment': self.investment.pk, 'date': '2026-01-01', 'type': 'aporte', 'amount': amount},
                user=self.user,
            )
            self.assertFalse(form.is_valid())

    def test_negative_service_amount_is_not_converted_to_positive(self):
        self.record(self.wallet)
        with self.assertRaises(ValidationError):
            self.apply(-100)
        self.assertEqual(self.value(), Decimal('0'))

    def test_optional_fields_can_be_explicitly_cleared(self):
        instance = self.record(due_date=date(2027, 1, 1), notes='Anterior')
        original = InvestmentTransaction.objects.get(pk=instance.pk)
        data = model_to_dict(instance)
        data.update({'notes': '', 'due_date': ''})
        form = InvestmentTransactionForm(data, instance=instance, user=self.user)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        InvestmentCrudView()._preserve_unrendered_fields_after_validation(form, original)
        Service.update(form, instance)
        instance.refresh_from_db()
        self.assertEqual((instance.notes, instance.due_date), ('', None))

    def test_api_rejects_other_users_investment_and_internal_fields(self):
        instance = self.record()
        other = User.objects.create(username='other', email='other@example.invalid')
        other_wallet = Service.get_or_create_default_wallet(other)
        for changes in ({'investment': other_wallet.pk}, {'user': other.pk}, {'operation_id': str(uuid.uuid4())}):
            data = {'amount': '1000', **changes}
            request = APIRequestFactory().patch('/', data, format='json')
            force_authenticate(request, user=self.user)
            response = APITransactionView.as_view({'patch': 'partial_update'})(request, pk=instance.pk)
            self.assertEqual(response.status_code, 400, response.data)
        instance.refresh_from_db()
        self.assertEqual(instance.investment_id, self.investment.pk)

    def test_api_investment_creation_rejects_foreign_asset(self):
        other = User.objects.create(username='other', email='other@example.invalid')
        other_wallet = Service.get_or_create_default_wallet(other)
        request = APIRequestFactory().post(
            '/',
            {
                'description': 'Outro',
                'asset': other_wallet.asset_id,
                'broker': self.wallet.broker_id,
                'start_date': '2026-01-01',
                'status': 'active',
            },
            format='json',
        )
        force_authenticate(request, user=self.user)
        response = APIInvestmentView.as_view({'post': 'create'})(request)
        self.assertEqual(response.status_code, 400)

    def test_api_validation_errors_return_400_not_404(self):
        statement = self.statement()
        instance = InvestmentTransaction.objects.get(statement_transaction=statement)
        request = APIRequestFactory().patch('/', {'notes': 'Não permitido'}, format='json')
        force_authenticate(request, user=self.user)
        response = APITransactionView.as_view({'patch': 'partial_update'})(request, pk=instance.pk)
        self.assertEqual(response.status_code, 400)

    def test_legacy_cross_user_rows_are_not_exposed_in_positions_or_charts(self):
        other = User.objects.create(username='other', email='other@example.invalid')
        other_wallet = Service.get_or_create_default_wallet(other)
        self.record(other_wallet)
        self.record(other_wallet, type='rendimento', amount=100)
        self.assertEqual(self.value(other_wallet), Decimal('0'))
        self.assertEqual(InvestmentService.get_dashboard(other)['total_income'], Decimal('0'))
        for dataset in InvestmentService.get_progression_datasets(other):
            self.assertFalse(dataset['values'])

    def test_application_view_handles_replay_without_server_error(self):
        funding = self.record(self.wallet)
        request = RequestFactory().post('/', {'investment': self.investment.pk, 'date': '2026-01-02', 'amount': '1000'})
        request.user = self.user
        view = InvestmentTransactionView()
        self.assertEqual(view.apply_from_wallet_transaction(request, funding.pk).status_code, 302)
        with patch.object(view, '_render', side_effect=lambda request, form, *args: form):
            form = view.apply_from_wallet_transaction(request, funding.pk)
        self.assertTrue(form.non_field_errors())
        self.assertEqual(self.value(), Decimal('1000'))


class InvestmentMigrationTests(TransactionTestCase):
    def test_legacy_funding_uuid_is_separated_without_changing_amounts(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('investments', '0004_investmenttransaction_due_date')])
        state = executor.loader.project_state([('investments', '0004_investmenttransaction_due_date')]).apps
        UserModel = state.get_model('login', 'User')
        BrokerModel = state.get_model('investments', 'Broker')
        AssetModel = state.get_model('investments', 'Asset')
        InvestmentModel = state.get_model('investments', 'Investment')
        Movement = state.get_model('investments', 'InvestmentTransaction')
        user = UserModel.objects.create(username='legacy', email='legacy@example.invalid')
        broker = BrokerModel.objects.create(description='Caixa de investimentos', kind='wallet', user=user)
        cash = AssetModel.objects.create(
            description='Disponível para investir', symbol='CASH-BRL', asset_type='currency', user=user
        )
        asset = AssetModel.objects.create(description='CDB', asset_type='fixed_income', user=user)
        wallet = InvestmentModel.objects.create(
            description='Caixa de investimentos BRL', asset=cash, broker=broker, user=user, start_date=date(2026, 1, 1)
        )
        destination = InvestmentModel.objects.create(
            description='CDB', asset=asset, broker=broker, user=user, start_date=date(2026, 1, 1)
        )
        operation = uuid.uuid4()
        common = dict(user=user, date=date(2026, 1, 1), amount=1000, operation_id=operation)
        funding = Movement.objects.create(**common, investment=wallet, type='aporte')
        debit = Movement.objects.create(**common, investment=wallet, type='resgate')
        credit = Movement.objects.create(**common, investment=destination, type='aporte')
        before = list(Movement.objects.order_by('pk').values_list('pk', 'amount', 'type', 'investment_id'))
        try:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            migrated = InvestmentTransaction.objects.get(pk=funding.pk)
            self.assertIsNone(migrated.operation_id)
            self.assertEqual(InvestmentTransaction.objects.get(pk=credit.pk).funding_transaction_id, funding.pk)
            self.assertEqual(Investment.objects.get(pk=wallet.pk).default_wallet_for_id, user.pk)
            self.assertEqual(
                before,
                list(InvestmentTransaction.objects.order_by('pk').values_list('pk', 'amount', 'type', 'investment_id')),
            )
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
