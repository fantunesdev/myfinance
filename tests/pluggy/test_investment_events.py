from datetime import date
from decimal import Decimal
from uuid import uuid4
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from bank_sync.models import (
    BankConnection,
    ExternalInvestment,
    InvestmentEvent,
    InvestmentHistoryJob,
    InvestmentCashEvidence,
    InvestmentReconciliationBaseline,
    ReconciledInvestmentOperation,
)
from bank_sync.investment_events import reconcile, classify
from investments.models import Asset, Broker, Investment, InvestmentTransaction
from investments.services.investment import InvestmentService
from investments.services.transaction import InvestmentTransactionService
from login.models import User


class EventTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='events', email='events@example.invalid')
        self.conn = BankConnection.objects.create(user=self.user, item_id=uuid4())
        self.wallet = InvestmentTransactionService.get_or_create_default_wallet(self.user)
        asset = Asset.objects.create(user=self.user, description='Ação', asset_type='variable_income')
        self.inv = Investment.objects.create(
            user=self.user,
            asset=asset,
            broker=self.wallet.broker,
            description='Ação',
            start_date=date(2020, 1, 1),
        )
        self.source = ExternalInvestment.objects.create(connection=self.conn, external_id=uuid4(), investment=self.inv)
        InvestmentTransaction.objects.create(
            user=self.user,
            investment=self.inv,
            date=date(2020, 1, 1),
            type='aporte',
            amount=1000,
            quantity=100,
        )
        self.job = InvestmentHistoryJob.objects.create(
            connection=self.conn, state='succeeded', finished_at=timezone.now()
        )
        self.event = InvestmentEvent.objects.create(
            connection=self.conn,
            external_id=str(uuid4()),
            last_seen_job=self.job,
            facts={
                'date': '2026-11-12T00:00:00Z',
                'type': 'INTEREST',
                'amount': 100,
                'netAmount': 85,
            },
        )
        self.event.investments.add(self.source)
        self.cash = InvestmentCashEvidence.objects.create(
            connection=self.conn,
            external_id=str(uuid4()),
            account_id=uuid4(),
            facts={
                'date': '2026-11-12T00:00:00Z',
                'type': 'CREDIT',
                'status': 'POSTED',
                'currencyCode': 'BRL',
                'amount': 85,
            },
        )

    def apply(self, **kw):
        return reconcile(
            self.user,
            self.event.pk,
            1,
            'apply',
            cash_ids=[self.cash.pk],
            evidence='Crédito líquido no extrato do banco.',
            **kw
        )

    def test_income_increases_cash_once_without_increasing_stock_value(self):
        operation = self.apply()
        self.assertEqual(self.apply().pk, operation.pk)
        self.assertEqual(InvestmentService.get_position(self.wallet)['value'], 85)
        pos = InvestmentService.get_position(self.inv)
        self.assertEqual(pos['value'], 1000)
        self.assertEqual(pos['income'], 100)
        self.assertEqual(pos['costs'], 15)
        self.assertEqual(pos['quantity'], 100)

    def test_liquidation_mismatch_rolls_back(self):
        self.cash.facts['amount'] = 90
        self.cash.save()
        with self.assertRaises(ValidationError):
            self.apply()
        self.assertFalse(ReconciledInvestmentOperation.objects.exists())
        self.assertEqual(InvestmentService.get_position(self.wallet)['value'], 0)

    def test_previous_baseline_cannot_be_reimported(self):
        self.event.state = 'historical'
        self.event.save()
        with self.assertRaises(ValidationError):
            self.apply()
        self.assertEqual(self.inv.transactions.count(), 1)

    def test_ambiguous_sell_is_not_a_sale_by_default(self):
        self.assertEqual(
            classify({'type': 'SELL', 'description': 'Rendimento', 'quantity': None})[0],
            'ambiguous',
        )

    def test_cash_cannot_be_reused(self):
        self.apply()
        other = InvestmentEvent.objects.create(
            connection=self.conn,
            external_id=str(uuid4()),
            last_seen_job=self.job,
            facts=self.event.facts,
        )
        other.investments.add(self.source)
        with self.assertRaises(ValidationError):
            reconcile(
                self.user,
                other.pk,
                1,
                'apply',
                cash_ids=[self.cash.pk],
                evidence='Tentativa de reaproveitamento.',
            )

    def test_failed_collection_cannot_be_applied(self):
        self.job.state = 'failed'
        self.job.save()
        with self.assertRaises(ValidationError):
            self.apply()

    def test_worker_command_loads_without_starting_external_queries(self):
        from django.core.management import call_command

        call_command('process_investment_history', once=True)

    def test_worker_finishes_a_queued_job(self):
        from unittest.mock import patch
        from django.core.management import call_command

        job = InvestmentHistoryJob.objects.create(connection=self.conn)
        with patch(
            'bank_sync.management.commands.process_investment_history.collect',
            return_value=12,
        ):
            call_command('process_investment_history', once=True)
        job.refresh_from_db()
        self.assertEqual(job.state, 'succeeded')
        self.conn.refresh_from_db()
        self.assertIsNone(self.conn.lease_token)

    def test_group_two_purchases_one_bank_debit(self):
        from bank_sync.investment_events import reconcile_purchase_group

        first = self.event
        first.facts = {
            'date': '2026-11-12T00:00:00Z',
            'type': 'BUY',
            'amount': 40,
            'netAmount': 40,
            'quantity': 4,
            'value': 10,
        }
        first.save()
        second = InvestmentEvent.objects.create(
            connection=self.conn,
            external_id=str(uuid4()),
            last_seen_job=self.job,
            facts={
                **first.facts,
                'amount': 60,
                'netAmount': 60,
                'quantity': 6,
            },
        )
        second.investments.add(self.source)
        self.cash.facts.update(type='DEBIT', amount=101)
        self.cash.save()
        credit = InvestmentTransaction.objects.create(
            user=self.user,
            investment=self.wallet,
            date=date(2026, 11, 12),
            type='aporte',
            amount=101,
        )
        op = reconcile_purchase_group(
            self.user,
            [
                {'id': first.pk, 'revision': 1},
                {'id': second.pk, 'revision': 1},
            ],
            [self.cash.pk],
            [{'credit_id': credit.pk, 'amount': '101'}],
            '1',
            'Nota: duas compras e R$1 de custo.',
        )
        self.assertEqual(op.kind, 'purchase_group')
        self.assertEqual(InvestmentService.get_position(self.wallet)['value'], 0)
        self.assertEqual(InvestmentService.get_position(self.inv)['quantity'], 110)
        self.assertEqual(reconcile(self.user, second.pk, 1, 'apply').pk, op.pk)

    def test_cash_income_is_not_unwithdrawn_income_in_the_security(self):
        self.apply()
        self.assertEqual(InvestmentService.get_position(self.inv)['unwithdrawn_income'], 0)

    def test_two_transfer_legs_preserve_total_and_generate_no_income(self):
        from bank_sync.investment_events import reconcile_transfer_group

        destination = Investment.objects.create(
            user=self.user,
            asset=self.inv.asset,
            broker=self.inv.broker,
            description='Custódia destino',
            start_date=date(2020, 1, 1),
        )
        other = ExternalInvestment.objects.create(connection=self.conn, external_id=uuid4(), investment=destination)
        self.event.facts = {
            'type': 'TRANSFER',
            'movementType': 'DEBIT',
            'date': '2026-11-12T00:00:00Z',
            'quantity': 20,
        }
        self.event.save()
        incoming = InvestmentEvent.objects.create(
            connection=self.conn,
            external_id=str(uuid4()),
            last_seen_job=self.job,
            facts={**self.event.facts, 'movementType': 'CREDIT'},
        )
        incoming.investments.add(other)
        reconcile_transfer_group(
            self.user,
            [
                {'id': self.event.pk, 'revision': 1},
                {'id': incoming.pk, 'revision': 1},
            ],
            '200',
            'Transferência de custódia comprovada.',
        )
        src = InvestmentService.get_position(self.inv)
        dst = InvestmentService.get_position(destination)
        self.assertEqual(src['value'] + dst['value'], 1000)
        self.assertEqual(src['quantity'], 80)
        self.assertEqual(dst['quantity'], 20)
        self.assertEqual(src['income'] + dst['income'], 0)

    def test_baseline_is_checked_even_if_event_state_is_new(self):
        InvestmentReconciliationBaseline.objects.create(
            investment=self.inv,
            date=date(2026, 11, 12),
            evidence='Abertura conferida.',
        )
        with self.assertRaises(ValidationError):
            self.apply()
        self.assertFalse(ReconciledInvestmentOperation.objects.exists())

    def test_price_factor_and_missing_gross_require_review(self):
        for facts in (
            {**self.event.facts, 'priceFactor': 100},
            {**self.event.facts, 'amount': None},
        ):
            self.event.facts = facts
            self.event.save()
            with self.assertRaises(ValidationError):
                self.apply()
        self.assertFalse(ReconciledInvestmentOperation.objects.exists())

    def test_sale_cannot_remove_more_principal_than_known(self):
        self.event.facts.update(type='SELL', quantity=10)
        self.event.save()
        with self.assertRaises(ValidationError):
            self.apply(principal='1001')
        self.assertEqual(InvestmentService.get_position(self.inv)['quantity'], 100)

    def test_source_revision_preserves_finances_and_requires_explicit_review(
        self,
    ):
        from unittest.mock import Mock
        from bank_sync.investment_events import collect

        operation = self.apply()
        reader = Mock()
        reader.request.return_value = {
            'status': 'UPDATED',
            'executionStatus': 'SUCCESS',
            'lastUpdatedAt': 'same',
        }
        reader.numbered.side_effect = [
            [
                {
                    'id': self.event.external_id,
                    **self.event.facts,
                    'netAmount': 80,
                }
            ],
            [],
        ]
        collect(self.job, reader=reader)
        self.event.refresh_from_db()
        operation.refresh_from_db()
        self.assertEqual(self.event.state, 'conflict')
        self.assertEqual(operation.state, 'conflict')
        self.assertEqual(self.event.revision, 2)
        self.assertEqual(self.event.revisions.count(), 1)
        self.assertEqual(InvestmentService.get_position(self.wallet)['value'], 85)
        with self.assertRaises(ValidationError):
            self.apply()
        reconcile(
            self.user,
            self.event.pk,
            2,
            'keep',
            evidence='Extrato original confirma os R$85; manter.',
        )
        self.event.refresh_from_db()
        self.assertEqual(self.event.state, 'linked')
        self.assertEqual(InvestmentService.get_position(self.wallet)['value'], 85)

    def test_cash_revision_has_history_and_flags_operation(self):
        from unittest.mock import Mock
        from bank_sync.investment_events import collect

        operation = self.apply()
        reader = Mock()
        reader.request.return_value = {
            'status': 'UPDATED',
            'executionStatus': 'SUCCESS',
        }
        reader.numbered.side_effect = [
            [{'id': self.event.external_id, **self.event.facts}],
            [{'id': str(self.cash.account_id), 'type': 'BANK'}],
        ]
        reader.transactions.return_value = [{'id': self.cash.external_id, **self.cash.facts, 'amount': 90}]
        collect(self.job, reader=reader)
        self.cash.refresh_from_db()
        operation.refresh_from_db()
        self.assertEqual(operation.state, 'conflict')
        self.assertEqual(self.cash.history[0]['facts']['amount'], 85)
        self.assertEqual(self.cash.revision, 2)
        self.assertEqual(InvestmentService.get_position(self.wallet)['value'], 85)

    def test_worker_collects_without_applying_income(self):
        from unittest.mock import patch
        from django.core.management import call_command

        InvestmentHistoryJob.objects.create(connection=self.conn)
        with patch(
            'bank_sync.management.commands.process_investment_history.collect',
            return_value=1,
        ):
            call_command('process_investment_history', once=True)
        self.assertFalse(ReconciledInvestmentOperation.objects.exists())
        self.assertEqual(InvestmentService.get_position(self.wallet)['value'], 0)

    def test_manual_application_cannot_reuse_cash_reserved_by_reconciliation(self):
        from bank_sync.models import CashAllocation

        credit = InvestmentTransaction.objects.create(
            user=self.user, investment=self.wallet, date=date(2026, 11, 12), type='aporte', amount=100
        )
        debit = InvestmentTransaction.objects.create(
            user=self.user, investment=self.wallet, date=date(2026, 11, 12), type='resgate', amount=80
        )
        CashAllocation.objects.create(credit=credit, debit=debit, amount=80)
        InvestmentTransaction.objects.create(
            user=self.user, investment=self.wallet, date=date(2026, 11, 12), type='aporte', amount=100
        )
        with self.assertRaises(ValidationError):
            InvestmentTransactionService.transfer_between_investments(
                self.wallet, self.inv, amount=50, date=date(2026, 11, 12), funding_transaction=credit
            )
        with self.assertRaises(ValidationError):
            InvestmentTransactionService.delete(credit)
        credit.amount = 70
        with self.assertRaises(ValidationError):
            InvestmentTransactionService.validate_funding(credit)
