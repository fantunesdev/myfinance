from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase

from investments.models import InvestmentTransaction
from investments.services.investment import InvestmentService
from investments.services.transaction import (
    InvestmentTransactionService as Service,
)
from login.models import User
from statement.models import Category, Currency, Subcategory, Transaction
from statement.services.core.transaction import TransactionService


class LegacyStatementSyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='legacy-sync', email='legacy-sync@test.invalid'
        )
        self.wallet = Service.get_or_create_default_wallet(self.user)
        Currency.objects.get_or_create(
            id='BRL', defaults={'description': 'Real', 'symbol': 'R$'}
        )
        self.category = Category.objects.create(
            description='Investimentos', type='saida'
        )
        self.subcategory = Subcategory.objects.create(
            description='Aportes', category=self.category, is_investment=True
        )
        self.other = Subcategory.objects.create(
            description='Outra', category=self.category
        )

    def statement(self, legacy=False, **overrides):
        instance = Transaction.objects.create(
            user=self.user,
            category=self.category,
            subcategory=self.subcategory,
            posted_date=date(2018, 1, 31),
            payment_date=date(2018, 1, 31),
            description='Aporte antigo',
            value=316.33,
            type='saida',
            effected=False,
            **overrides
        )
        if legacy:
            # Imported cash already contains the amount, but the historical
            # statement association was not recorded. Do not run save signals.
            InvestmentTransaction.objects.filter(
                statement_transaction=instance
            ).update(statement_transaction=None)
        return instance

    def cash(self):
        return InvestmentService.get_position(self.wallet)['value']

    def test_repeated_legacy_description_edits_do_not_duplicate_or_link_deposits(
        self,
    ):
        statement = self.statement(legacy=True)
        count = self.wallet.transactions.count()
        for description in ['Descrição corrigida', 'Outra descrição']:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                statement.description = description
                statement.observation = 'Anotação'
                statement.save()
            self.assertEqual(callbacks, [])
            self.assertEqual(self.cash(), Decimal('316.33'))
            self.assertEqual(self.wallet.transactions.count(), count)
            self.assertFalse(
                InvestmentTransaction.objects.filter(
                    statement_transaction=statement
                ).exists()
            )
            self.assertFalse(
                hasattr(statement, '_investment_previous_statement')
            )

    def test_legacy_partial_save_ignores_unsaved_financial_fields(self):
        statement = self.statement(legacy=True)
        statement.description = 'Descrição parcial'
        statement.value = 9999
        statement.payment_date = date(2027, 1, 1)
        statement.subcategory = self.other
        statement.save(update_fields=['description'])
        statement.refresh_from_db()
        self.assertEqual(statement.value, 316.33)
        self.assertEqual(statement.payment_date, date(2018, 1, 31))
        self.assertEqual(statement.subcategory_id, self.subcategory.pk)
        self.assertEqual(self.cash(), Decimal('316.33'))
        self.assertEqual(self.wallet.transactions.count(), 1)

    def test_linked_partial_save_also_uses_only_persisted_values(self):
        statement = self.statement()
        statement.description = 'Descrição parcial'
        statement.value = 9999
        statement.save(update_fields=['description'])
        funding = InvestmentTransaction.objects.get(
            statement_transaction=statement
        )
        self.assertEqual(funding.amount, Decimal('316.33'))
        self.assertEqual(funding.notes, 'Descrição parcial')
        self.assertEqual(self.cash(), Decimal('316.33'))

    def test_legacy_financial_edits_are_rejected_and_rolled_back(self):
        for change in [
            {'value': 500},
            {'payment_date': date(2018, 2, 1)},
            {'type': 'entrada'},
            {'subcategory': self.other},
        ]:
            with self.subTest(change=change):
                statement = self.statement(legacy=True)
                old_rows = list(
                    self.wallet.transactions.order_by('pk').values()
                )
                for key, value in change.items():
                    setattr(statement, key, value)
                with self.captureOnCommitCallbacks(execute=True) as callbacks:
                    with self.assertRaisesRegex(
                        ValidationError, 'vínculo confirmado'
                    ):
                        statement.save()
                statement.refresh_from_db()
                self.assertEqual(statement.value, 316.33)
                self.assertEqual(statement.payment_date, date(2018, 1, 31))
                self.assertEqual(statement.type, 'saida')
                self.assertEqual(statement.subcategory_id, self.subcategory.pk)
                self.assertEqual(
                    list(self.wallet.transactions.order_by('pk').values()),
                    old_rows,
                )
                self.assertEqual(callbacks, [])

    def test_legacy_delete_is_protected_in_service_instance_and_queryset(self):
        statement = self.statement(legacy=True)
        pk = statement.pk
        for deletion in [
            lambda: TransactionService.delete(statement),
            lambda: statement.delete(),
            lambda: Transaction.objects.filter(pk=pk).delete(),
        ]:
            with self.subTest(deletion=deletion):
                with self.assertRaisesRegex(
                    ValidationError, 'vínculo confirmado'
                ):
                    with transaction.atomic():
                        deletion()
                self.assertTrue(Transaction.objects.filter(pk=pk).exists())
                self.assertEqual(self.cash(), Decimal('316.33'))

    def test_explicit_replay_without_creation_context_does_not_guess_a_link(
        self,
    ):
        statement = self.statement(legacy=True)
        with self.assertRaisesRegex(ValidationError, 'vínculo confirmado'):
            Service.create_wallet_contribution_from_statement_transaction(
                statement
            )
        self.assertEqual(self.cash(), Decimal('316.33'))
        self.assertEqual(self.wallet.transactions.count(), 1)

    def test_existing_linked_entries_still_sync_edits_and_delete(self):
        statement = self.statement()
        statement.value = 500
        statement.save()
        self.assertEqual(self.cash(), Decimal('500'))
        TransactionService.delete(statement)
        self.assertEqual(self.cash(), Decimal('0'))
        self.assertFalse(Transaction.objects.filter(user=self.user).exists())

    def test_intentional_recategorization_of_non_investment_creates_one_deposit(
        self,
    ):
        statement = self.statement()
        statement.subcategory = self.other
        statement.save()
        self.assertEqual(self.cash(), Decimal('0'))
        statement.subcategory = self.subcategory
        statement.save()
        self.assertEqual(self.cash(), Decimal('316.33'))
        statement.description = 'Reclassificado'
        statement.save()
        self.assertEqual(self.wallet.transactions.count(), 1)

    def test_effected_changes_do_not_change_cash_or_auto_link_legacy_entries(
        self,
    ):
        statement = self.statement(legacy=True)
        statement.effected = True
        statement.save()
        statement.effected = False
        statement.save()
        self.assertEqual(self.cash(), Decimal('316.33'))
        self.assertFalse(
            InvestmentTransaction.objects.filter(
                statement_transaction=statement
            ).exists()
        )
