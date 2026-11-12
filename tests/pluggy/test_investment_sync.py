from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase
from bank_sync.models import BankConnection, ExternalInvestment, InvestmentSnapshot
from bank_sync.investments import sync_investments
from clients.pluggy.reader import ProbeError
from investments.models import Asset, Broker, Investment, InvestmentTransaction
from investments.services.investment import InvestmentService
from login.models import User


class Reader:
    def __init__(self, rows): self.rows = rows
    def authenticate(self): pass
    def request(self, *args):
        return {'status': 'UPDATED', 'executionStatus': 'SUCCESS', 'lastUpdatedAt': '2026-11-11T14:00:00Z'}
    def numbered(self, *args): return self.rows


class PositionSyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='sync', email='sync@example.invalid')
        self.connection = BankConnection.objects.create(user=self.user, item_id=uuid4())
        self.external_id = uuid4()
        asset = Asset.objects.create(user=self.user, description='Ação', symbol='TEST3', asset_type='variable_income')
        broker = Broker.objects.create(user=self.user, description='Inter')
        self.inv = Investment.objects.create(user=self.user, asset=asset, broker=broker, description='Posição', start_date=date(2020,1,1), notes=str(self.external_id))
        InvestmentTransaction.objects.create(user=self.user, investment=self.inv, date=date(2020,1,1), type='aporte', amount=100, quantity=10)
        self.row = {'id': str(self.external_id), 'name': 'TEST3', 'status':'ACTIVE', 'currencyCode':'BRL', 'date':'2026-11-10T03:00:00Z', 'quantity':12, 'balance':150}

    def sync(self, rows=None): return sync_investments(self.connection, Reader(rows or [self.row]))

    def test_idempotent_updates_quantity_without_fabricating_income(self):
        self.assertEqual(self.sync()['updated'], 1)
        self.assertEqual(self.sync()['unchanged'], 1)
        self.assertEqual(InvestmentSnapshot.objects.count(), 1)
        position = InvestmentService.get_position(self.inv)
        self.assertEqual(position['value'], Decimal('150'))
        self.assertEqual(position['quantity'], Decimal('12'))
        self.assertEqual(position['income'], 0)
        self.assertEqual(position['invested'], 100)
        self.assertIsNone(InvestmentService.get_average_purchase_price(self.inv))

    def test_invalid_page_preserves_entire_portfolio(self):
        with self.assertRaises(ProbeError): self.sync([self.row, {**self.row,'id':str(uuid4()),'balance':'NaN'}])
        self.assertFalse(ExternalInvestment.objects.exists())
        self.assertEqual(self.inv.transactions.count(), 1)

    def test_unlinked_position_is_pending_not_duplicated(self):
        self.row['id'] = str(uuid4())
        self.assertEqual(self.sync()['pending'], 1)
        self.assertEqual(Investment.objects.count(), 1)
        self.assertEqual(self.inv.transactions.count(), 1)

    def test_missing_position_does_not_close_existing(self):
        self.sync()
        self.assertEqual(sync_investments(self.connection, Reader([]))['updated'], 0)
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.status, 'active')
        self.assertEqual(InvestmentService.get_position(self.inv)['value'], 150)

    def test_explicit_closed_position_sets_value_and_quantity_zero(self):
        self.row.update(status='TOTAL_WITHDRAWAL', balance=0, quantity=0)
        self.sync()
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.status, 'closed')
        self.assertEqual(InvestmentService.get_position(self.inv)['quantity'], 0)

    def test_other_owners_notes_cannot_be_linked(self):
        other = User.objects.create(username='other', email='other@example.invalid')
        self.inv.user = other
        self.inv.save()
        self.assertEqual(self.sync()['pending'], 1)
        self.assertFalse(ExternalInvestment.objects.get().investment_id)

    def test_unallocated_cash_blocks_position_update(self):
        from investments.services.transaction import InvestmentTransactionService
        from django.core.exceptions import ValidationError
        wallet = InvestmentTransactionService.get_or_create_default_wallet(self.user)
        InvestmentTransaction.objects.create(user=self.user, investment=wallet, date=date(2026,1,1),type='aporte',amount=100)
        with self.assertRaises(ValidationError): self.sync()
        self.assertFalse(InvestmentSnapshot.objects.exists())
        self.assertEqual(InvestmentService.get_position(self.inv)['value'],100)

    def test_failure_after_first_position_rolls_back_all_updates(self):
        other = User.objects.create(username='third', email='third@example.invalid')
        foreign = Investment.objects.create(user=other,asset=self.inv.asset,broker=self.inv.broker,description='Foreign',start_date=date(2020,1,1))
        external_id = uuid4()
        ExternalInvestment.objects.create(connection=self.connection,external_id=external_id,investment=foreign)
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):self.sync([self.row,{**self.row,'id':str(external_id)}])
        self.assertFalse(InvestmentSnapshot.objects.exists())
        self.assertEqual(self.inv.transactions.count(),1)
