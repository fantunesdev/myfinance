from datetime import date
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch
import json

from django.test import TestCase, RequestFactory

from bank_sync.event_import import import_events
from bank_sync.models import (BankConnection, ExternalInvestment, InvestmentCashEvidence, InvestmentEvent,
                             InvestmentHistoryJob, InvestmentReconciliationBaseline, ReconciledInvestmentOperation)
from bank_sync.views import sync_investment_positions
from investments.models import Asset, Broker, Investment, InvestmentTransaction as M
from investments.services.investment import InvestmentService as Positions
from investments.services.transaction import InvestmentTransactionService as Service
from login.models import User


class EventImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='event-import', email='event-import@example.invalid')
        self.connection = BankConnection.objects.create(user=self.user, item_id=uuid4())
        self.job = InvestmentHistoryJob.objects.create(connection=self.connection, state='succeeded')
        self.wallet = Service.get_or_create_default_wallet(self.user)
        self.funding = M.objects.create(user=self.user, investment=self.wallet, date=date(2026, 11, 1), type='aporte', amount=1000)
        broker = Broker.objects.create(user=self.user, description='Inter', kind='bank')
        asset = Asset.objects.create(user=self.user, description='CDB Inter', asset_type='fixed_income')
        self.inv = Investment.objects.create(user=self.user, asset=asset, broker=broker, description='CDB Inter', start_date=date(2026, 11, 1))
        M.objects.create(user=self.user, investment=self.inv, date=date(2026, 11, 1), type='aporte', amount=100, quantity=100)
        InvestmentReconciliationBaseline.objects.create(investment=self.inv, date=date(2026, 11, 1), evidence='Abertura')
        self.source = ExternalInvestment.objects.create(connection=self.connection, external_id=uuid4(), investment=self.inv,
            facts={'name': 'CDB Inter', 'currencyCode': 'BRL', 'type': 'FIXED_INCOME'})
        self.account = uuid4()

    def event(self, kind='BUY', gross=100, net=100, qty=100, source=None, expenses=None):
        event = InvestmentEvent.objects.create(connection=self.connection, external_id=str(uuid4()), state='new',
            last_seen_job=self.job, facts={'date': '2026-11-12T00:00:00Z', 'type': kind,
                'quantity': qty, 'amount': gross, 'netAmount': net, 'value': 1, 'expenses': expenses})
        event.investments.add(source or self.source)
        return event

    def cash(self, kind='DEBIT', value=-100, description='Aplicação - CDB Inter'):
        return InvestmentCashEvidence.objects.create(connection=self.connection, external_id=str(uuid4()), account_id=self.account,
            facts={'date': '2026-11-12T00:00:00Z', 'type': kind, 'amount': value, 'description': description,
                   'status': 'POSTED', 'currencyCode': 'BRL'})

    def test_complete_purchase_is_recorded_and_retries_do_not_duplicate(self):
        event = self.event()
        self.cash()
        result = import_events(self.connection)
        self.assertEqual(result['applied'], [event.pk])
        self.assertEqual(Positions.get_position(self.inv)['value'], 200)
        self.assertEqual(Positions.get_position(self.wallet)['value'], 900)
        op = ReconciledInvestmentOperation.objects.get(event=event)
        self.assertTrue(op.automatic)
        self.assertTrue(self.funding.cash_allocations_out.filter(amount=100).exists())
        count = M.objects.count()
        self.assertEqual(import_events(self.connection), {'applied': [], 'adopted': []})
        self.assertEqual(M.objects.count(), count)

    def test_paid_income_goes_to_wallet_without_increasing_the_position_again(self):
        event = self.event(kind='INTEREST', gross=10, net=8, qty=None, expenses={'incomeTax': 2})
        self.cash('CREDIT', 8, 'Rendimento - CDB Inter')
        self.assertEqual(import_events(self.connection)['applied'], [event.pk])
        self.assertEqual(Positions.get_position(self.inv)['value'], 100)
        self.assertEqual(Positions.get_position(self.wallet)['value'], 1008)
        self.assertEqual(Positions.get_position(self.inv)['income'] - Positions.get_position(self.inv)['costs'], 8)

    def test_redemption_uses_known_cost_and_does_not_leave_negative_unwithdrawn_income(self):
        event = self.event(kind='SELL', gross=110, net=108, expenses={'incomeTax': 2})
        self.cash('CREDIT', 108, 'Resgate - CDB Inter')
        self.assertEqual(import_events(self.connection)['applied'], [event.pk])
        pos = Positions.get_position(self.inv)
        self.assertEqual(pos['value'], 0)
        self.assertEqual(pos['quantity'], 0)
        self.assertEqual(pos['remaining_principal'], 0)
        self.assertEqual(pos['unwithdrawn_income'], 0)
        self.assertEqual(Positions.get_position(self.wallet)['value'], 1108)

    def test_new_fixed_income_title_is_created_from_purchase_and_official_position(self):
        source = ExternalInvestment.objects.create(connection=self.connection, external_id=uuid4(),
            facts={'name': 'LCI Inter', 'currencyCode': 'BRL', 'type': 'FIXED_INCOME', 'subtype': 'LCI', 'status': 'ACTIVE',
                   'purchaseDate': '2026-11-12T00:00:00Z', 'date': '2026-11-12T14:00:00Z', 'balance': 101,
                   'quantity': 100, 'amount': 101, 'value': 1.01, 'dueDate': None})
        event = self.event(source=source)
        self.cash(description='Aplicação - LCI Inter')
        self.assertEqual(import_events(self.connection)['applied'], [event.pk])
        source.refresh_from_db()
        self.assertIsNotNone(source.investment_id)
        pos = Positions.get_position(source.investment)
        self.assertEqual(pos['value'], 101)
        self.assertEqual(pos['quantity'], 100)
        self.assertEqual(pos['remaining_principal'], 100)
        self.assertEqual(source.snapshots.count(), 1)
        self.assertEqual(Positions.get_position(self.wallet)['value'], 900)

    def test_missing_cash_or_quantity_does_not_create_financial_rows(self):
        event = self.event(qty=None)
        before = list(M.objects.order_by('pk').values())
        self.assertEqual(import_events(self.connection)['applied'], [])
        self.cash()
        self.assertEqual(import_events(self.connection)['applied'], [])
        self.assertEqual(list(M.objects.order_by('pk').values()), before)
        event.refresh_from_db()
        self.assertEqual(event.state, 'new')
        self.assertTrue(event.reason)

    def test_new_equity_with_explicit_ticker_is_created_without_guessing_the_asset(self):
        source = ExternalInvestment.objects.create(connection=self.connection, external_id=uuid4(),
            facts={'name': 'TEST3', 'currencyCode': 'BRL', 'type': 'EQUITY', 'status': 'ACTIVE',
                   'purchaseDate': None, 'date': '2026-11-12T14:00:00Z', 'balance': 101,
                   'quantity': 100, 'amount': 101, 'value': 1.01, 'dueDate': None})
        event = self.event(source=source)
        self.cash(description='Débito B3 - Nota Bov 12/11/2026')
        self.assertEqual(import_events(self.connection)['applied'], [event.pk])
        source.refresh_from_db()
        self.assertEqual(source.investment.asset.symbol, 'TEST3')
        self.assertEqual(source.investment.asset.asset_type, 'variable_income')
        self.assertEqual(Positions.get_position(source.investment)['value'], 101)

    def test_two_competing_events_and_existing_unlinked_records_are_not_duplicated(self):
        self.event()
        self.event()
        self.cash()
        before = M.objects.count()
        self.assertEqual(import_events(self.connection)['applied'], [])
        self.assertEqual(M.objects.count(), before)
        InvestmentEvent.objects.all().delete()
        self.event()
        M.objects.create(user=self.user, investment=self.inv, date=date(2026, 11, 12), type='aporte', amount=100, quantity=100)
        before = M.objects.count()
        self.assertEqual(import_events(self.connection)['applied'], [])
        self.assertEqual(M.objects.count(), before)

    def test_positions_refresh_queues_history_without_duplicate_jobs(self):
        with patch('bank_sync.investments.sync_investments', return_value={'checked': 1, 'updated': 0}):
            for _ in range(2):
                request = RequestFactory().post('/', '{}', content_type='application/json')
                request.user = self.user
                response = sync_investment_positions(request)
                self.assertEqual(response.status_code, 200)
                self.assertIn('history_job_id', json.loads(response.content))
        self.assertEqual(InvestmentHistoryJob.objects.filter(state='queued').count(), 1)
