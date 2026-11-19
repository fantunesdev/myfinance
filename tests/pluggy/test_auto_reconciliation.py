from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
import json
from unittest.mock import Mock, patch
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, RequestFactory
from django.utils import timezone

from bank_sync.auto_reconciliation import auto_reconcile
from bank_sync.cash_reviews import bank_rows
from bank_sync.event_views import auto_link, event_list
from bank_sync.investment_events import collect, reconcile
from bank_sync.models import (BankConnection, ExternalInvestment, InvestmentCashEvidence, InvestmentCashReview,
                             InvestmentEvent, InvestmentHistoryJob, InvestmentReconciliationBaseline,
                             ReconciledInvestmentOperation)
from investments.models import Asset, Broker, Investment, InvestmentTransaction as Movement
from investments.services.transaction import InvestmentTransactionService as Service
from login.models import User


class AutomaticReconciliationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='auto-link', email='auto-link@example.invalid')
        self.connection = BankConnection.objects.create(user=self.user, item_id=uuid4())
        self.wallet = Service.get_or_create_default_wallet(self.user)
        broker = Broker.objects.create(user=self.user, description='Inter', kind='bank')
        asset = Asset.objects.create(user=self.user, description='LCI', symbol='LCI', asset_type='fixed_income')
        self.investment = Investment.objects.create(user=self.user, asset=asset, broker=broker,
                                                    description='Inter LCI', start_date=date(2026, 1, 1))
        self.source = ExternalInvestment.objects.create(connection=self.connection, external_id=uuid4(),
                                                        investment=self.investment)
        self.job = InvestmentHistoryJob.objects.create(connection=self.connection, state='succeeded',
                                                       finished_at=timezone.now())
        self.event = InvestmentEvent.objects.create(connection=self.connection, external_id=str(uuid4()),
            last_seen_job=self.job, facts={'type': 'SELL', 'date': '2026-11-12T00:00:00Z',
                                          'netAmount': 100, 'amount': 101, 'quantity': 10})
        self.event.investments.add(self.source)
        operation = uuid4()
        self.movement = Movement.objects.create(user=self.user, investment=self.investment,
            date=date(2026, 11, 12), type='resgate', amount=100, quantity=10, operation_id=operation)
        self.counterpart = Movement.objects.create(user=self.user, investment=self.wallet,
            date=date(2026, 11, 12), type='aporte', amount=100, operation_id=operation)
        self.cash = InvestmentCashEvidence.objects.create(connection=self.connection, external_id=str(uuid4()),
            account_id=uuid4(), facts={'type': 'CREDIT', 'date': '2026-11-12T00:00:00Z', 'amount': 100,
                                      'description': 'Resgate - LCI Inter', 'status': 'POSTED', 'currencyCode': 'BRL'})

    def test_exact_event_and_bank_evidence_link_once_without_changing_money(self):
        before = list(Movement.objects.order_by('pk').values())
        preview = auto_reconcile(self.connection, dry_run=True)
        self.assertEqual(len(preview['events']), 1)
        self.assertFalse(ReconciledInvestmentOperation.objects.exists())
        applied = auto_reconcile(self.connection)
        self.assertEqual(preview, applied)
        self.event.refresh_from_db()
        self.assertEqual(self.event.state, 'linked')
        self.assertTrue(self.event.operation.automatic)
        self.assertEqual(set(self.event.operation.movements.values_list('pk', flat=True)),
                         {self.movement.pk, self.counterpart.pk})
        self.assertTrue(self.event.operation.cash_evidence.filter(pk=self.cash.pk).exists())
        self.assertEqual(list(Movement.objects.order_by('pk').values()), before)
        self.assertEqual(auto_reconcile(self.connection), {'events': [], 'bank_entries': []})

    def test_documented_historical_origin_can_link_without_inventing_quantity(self):
        origin = Investment.objects.create(user=self.user, asset=self.investment.asset,
            broker=self.investment.broker, description='LCI consolidada', start_date=date(2020, 1, 1))
        InvestmentReconciliationBaseline.objects.create(investment=self.investment,
            date=date(2026, 11, 15), evidence='Abertura auditada')
        opening = uuid4()
        for investment, kind in [(origin, 'resgate'), (self.investment, 'aporte')]:
            Movement.objects.create(user=self.user, investment=investment, type=kind,
                                    amount=500, date=date(2026, 11, 15), operation_id=opening)
        self.movement.investment = origin
        self.movement.quantity = None
        self.movement.save()
        self.event.state = 'historical'
        self.event.save()
        before = list(Movement.objects.order_by('pk').values())
        self.assertEqual(len(auto_reconcile(self.connection)['events']), 1)
        self.assertEqual(list(Movement.objects.order_by('pk').values()), before)

    def test_failed_collection_never_links_partially_fetched_records(self):
        job = InvestmentHistoryJob.objects.create(connection=self.connection)
        with patch('bank_sync.management.commands.process_investment_history.collect',
                   side_effect=RuntimeError('Falha durante a coleta')):
            call_command('process_investment_history', once=True)
        job.refresh_from_db()
        self.assertEqual(job.state, 'failed')
        self.assertFalse(ReconciledInvestmentOperation.objects.exists())
        with self.assertRaises(ValidationError):
            auto_reconcile(self.connection)

    def test_missing_quantity_different_date_or_missing_bank_never_links(self):
        self.event.facts['quantity'] = None
        self.event.save()
        self.assertEqual(auto_reconcile(self.connection), {'events': [], 'bank_entries': []})
        self.event.facts['quantity'] = 10
        self.event.save()
        self.cash.facts['date'] = '2026-11-13T00:00:00Z'
        self.cash.save()
        self.assertFalse(auto_reconcile(self.connection)['events'])
        self.cash.delete()
        self.assertFalse(auto_reconcile(self.connection)['events'])

    def test_pix_same_amount_is_not_a_redemption_receipt(self):
        self.cash.facts['description'] = 'Pix recebido - mesma quantia'
        self.cash.save()
        self.assertEqual(auto_reconcile(self.connection), {'events': [], 'bank_entries': []})

    def test_collection_preserves_an_ignored_event_and_its_justification(self):
        from bank_sync.investment_events import FIELDS
        self.event.facts = {key: self.event.facts.get(key) for key in FIELDS}
        self.event.state = 'ignored'
        self.event.reason = 'Decisão manual preservada'
        self.event.save()
        reader = Mock()
        reader.request.return_value = {'status': 'UPDATED', 'executionStatus': 'SUCCESS', 'lastUpdatedAt': 'same'}
        reader.numbered.side_effect = [[{'id': self.event.external_id, **self.event.facts}], []]
        collect(self.job, reader=reader)
        self.event.refresh_from_db()
        self.assertEqual(self.event.state, 'ignored')
        self.assertEqual(self.event.reason, 'Decisão manual preservada')

    def test_two_bank_credits_or_two_events_remain_ambiguous(self):
        duplicate = InvestmentCashEvidence.objects.create(connection=self.connection, external_id=str(uuid4()),
                                                         account_id=uuid4(), facts=self.cash.facts)
        self.assertEqual(auto_reconcile(self.connection), {'events': [], 'bank_entries': []})
        duplicate.delete()
        event = InvestmentEvent.objects.create(connection=self.connection, external_id=str(uuid4()),
                                               last_seen_job=self.job, facts=self.event.facts)
        event.investments.add(self.source)
        self.assertEqual(auto_reconcile(self.connection), {'events': [], 'bank_entries': []})

    def test_two_matching_movements_are_not_automatically_resolved(self):
        op = uuid4()
        for investment, kind in [(self.investment, 'resgate'), (self.wallet, 'aporte')]:
            Movement.objects.create(user=self.user, investment=investment, type=kind, amount=100,
                                    date=self.movement.date, quantity=10, operation_id=op)
        self.assertEqual(auto_reconcile(self.connection), {'events': [], 'bank_entries': []})

    def test_bank_only_requires_asset_family_custody_and_balanced_pair(self):
        self.event.delete()
        before = list(Movement.objects.values())
        result = auto_reconcile(self.connection)
        self.assertEqual(result['bank_entries'], [{'cash_id': self.cash.pk, 'movement_id': self.movement.pk}])
        review = InvestmentCashReview.objects.get()
        self.assertTrue(review.automatic)
        self.assertEqual(list(Movement.objects.values()), before)
        self.assertEqual(auto_reconcile(self.connection)['bank_entries'], [])

    def test_bank_only_wrong_family_missing_pair_or_multiple_custodies_stays_pending(self):
        self.event.delete()
        self.cash.facts['description'] = 'Resgate - CDB Inter'
        self.cash.save()
        self.assertFalse(auto_reconcile(self.connection)['bank_entries'])
        self.cash.facts['description'] = 'Resgate - LCI Inter'
        self.cash.save()
        another = BankConnection.objects.create(user=self.user, item_id=uuid4())
        other_source = ExternalInvestment.objects.create(connection=another, external_id=uuid4())
        # A second mapped title at the same broker makes custody ambiguous.
        inv = Investment.objects.create(user=self.user, asset=self.investment.asset, broker=self.investment.broker,
                                       description='Outra LCI', start_date=self.investment.start_date)
        other_source.investment = inv
        other_source.save()
        self.assertFalse(auto_reconcile(self.connection)['bank_entries'])
        other_source.delete()
        self.counterpart.delete()
        self.assertFalse(auto_reconcile(self.connection)['bank_entries'])

    def test_revision_or_explicit_ignore_is_never_automatically_overridden(self):
        self.event.revision = 2
        self.event.save()
        self.assertEqual(auto_reconcile(self.connection), {'events': [], 'bank_entries': []})
        self.event.state = 'ignored'
        self.event.reason = 'Decisão manual preservada'
        self.event.save()
        self.assertFalse(auto_reconcile(self.connection)['events'])
        self.event.delete()
        self.cash.revision = 2
        self.cash.save()
        self.assertFalse(auto_reconcile(self.connection)['bank_entries'])

    def test_failed_running_or_incomplete_job_blocks_automatic_links(self):
        for state in ['failed', 'running', 'queued']:
            self.job.state = state
            self.job.save()
            with self.assertRaises(ValidationError):
                auto_reconcile(self.connection)
        self.job.state = 'succeeded'
        self.job.save()
        self.connection.lease_token = uuid4()
        self.connection.lease_until = timezone.now() + timedelta(minutes=5)
        self.connection.save()
        with self.assertRaises(ValidationError):
            auto_reconcile(self.connection)

    def test_manual_import_link_is_preserved_on_repeated_automatic_runs(self):
        operation = reconcile(self.user, self.event.pk, 1, 'link', movement_ids=[self.movement.pk],
                              cash_ids=[self.cash.pk], evidence='Vínculo já guardado pela importação.')
        self.assertEqual(auto_reconcile(self.connection), {'events': [], 'bank_entries': []})
        self.event.refresh_from_db()
        self.assertEqual(self.event.operation.pk, operation.pk)
        self.assertFalse(self.event.operation.automatic)

    def test_worker_automatically_links_only_after_successful_collection(self):
        job = InvestmentHistoryJob.objects.create(connection=self.connection)
        def collected(current_job, **kwargs):
            self.event.last_seen_job = current_job
            self.event.save()
            return 1
        with patch('bank_sync.management.commands.process_investment_history.collect', side_effect=collected):
            call_command('process_investment_history', once=True)
        job.refresh_from_db()
        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(job.progress['automatic_events'], 1)
        self.assertTrue(ReconciledInvestmentOperation.objects.get().automatic)

    def test_worker_failure_rolls_back_all_new_links(self):
        job = InvestmentHistoryJob.objects.create(connection=self.connection)
        def collected(current_job, **kwargs):
            self.event.last_seen_job = current_job
            self.event.save()
            return 1
        def fail_after_link(*args, **kwargs):
            auto_reconcile(*args, **kwargs)
            raise ValidationError('Falha simulada antes de concluir o lote')
        with patch('bank_sync.management.commands.process_investment_history.collect', side_effect=collected), \
             patch('bank_sync.management.commands.process_investment_history.auto_reconcile', side_effect=fail_after_link):
            call_command('process_investment_history', once=True)
        job.refresh_from_db()
        self.event.refresh_from_db()
        self.assertEqual(job.state, 'failed')
        self.assertEqual(self.event.state, 'new')
        self.assertFalse(ReconciledInvestmentOperation.objects.exists())

    def test_command_is_preview_by_default_and_api_is_post_only(self):
        output = StringIO()
        call_command('reconcile_investment_history', connection=self.connection.pk, stdout=output)
        self.assertFalse(json.loads(output.getvalue())['applied'])
        self.assertFalse(ReconciledInvestmentOperation.objects.exists())
        request = RequestFactory().get('/')
        request.user = self.user
        self.assertEqual(auto_link(request).status_code, 405)

    def test_historical_bank_receipts_are_consultable_without_being_declared_matched(self):
        InvestmentReconciliationBaseline.objects.create(investment=self.investment,
            date=date(2026, 11, 15), evidence='Abertura auditada')
        request = RequestFactory().get('/', {'state': 'bank'})
        request.user = self.user
        data = json.loads(event_list(request).content)
        self.assertEqual(data['summary']['bank_pending'], 0)
        self.assertEqual(data['summary']['bank_prior'], 1)
        request = RequestFactory().get('/', {'state': 'bank_prior'})
        request.user = self.user
        data = json.loads(event_list(request).content)
        self.assertEqual(data['bank_entries'][0]['id'], self.cash.pk)
        self.assertIsNone(data['bank_entries'][0]['review'])
        self.assertFalse(InvestmentCashReview.objects.exists())
