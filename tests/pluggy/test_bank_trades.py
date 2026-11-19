from datetime import date
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, RequestFactory
from django.utils.dateparse import parse_datetime

from bank_sync.bank_trades import purchase_options, register_purchase
from bank_sync.models import (BankConnection, ExternalInvestment, InvestmentBankTrade, InvestmentCashEvidence,
    InvestmentCashReview, InvestmentEvent, InvestmentHistoryJob, InvestmentReconciliationBaseline,
    InvestmentSnapshot, ReconciledInvestmentOperation)
from bank_sync.event_views import bank_purchase
from investments.models import Asset, Broker, Investment, InvestmentTransaction as M
from investments.services.investment import InvestmentService as Positions
from investments.services.transaction import InvestmentTransactionService as Service
from login.models import User


class BankTradeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='bank-trade', email='bank-trade@example.invalid')
        self.other = User.objects.create(username='bank-other', email='bank-other@example.invalid')
        self.connection = BankConnection.objects.create(user=self.user, item_id=uuid4())
        InvestmentHistoryJob.objects.create(connection=self.connection, state='succeeded')
        self.wallet = Service.get_or_create_default_wallet(self.user)
        broker = Broker.objects.create(user=self.user, description='Inter', kind='bank')
        asset = Asset.objects.create(user=self.user, description='CDB Inter', asset_type='fixed_income')
        self.source_inv = Investment.objects.create(user=self.user, asset=asset, broker=broker, description='CDB Individual',
                                                    start_date=date(2026, 11, 6), status='closed')
        self.legacy = Investment.objects.create(user=self.user, asset=asset, broker=broker,
                                                description='CDB consolidado', start_date=date(2020, 1, 1))
        M.objects.create(user=self.user, investment=self.legacy, date=date(2020, 1, 1), type='aporte', amount=5000)
        self.source = ExternalInvestment.objects.create(connection=self.connection, external_id=uuid4(),
            investment=self.source_inv, reference_at=parse_datetime('2026-11-16T14:00:00Z'),
            facts={'name': 'CDB Inter', 'type': 'FIXED_INCOME', 'currencyCode': 'BRL', 'status': 'TOTAL_WITHDRAWAL',
                   'balance': '0', 'quantity': '0', 'purchaseDate': '2026-11-06T00:00:00Z'})
        InvestmentReconciliationBaseline.objects.create(investment=self.source_inv, date=date(2026, 11, 11), evidence='Auditoria')
        self.account = uuid4()
        self.buy_cash = self.cash('DEBIT', -1000, '2026-11-06T12:00:00Z', 'Aplicação - CDB Inter')
        self.buy = self.event('BUY', '2026-11-06T00:00:00Z', 1000, 1000, 1000)
        self.buy_op = ReconciledInvestmentOperation.objects.create(event=self.buy, kind='buy', state='linked', evidence='Abertura')
        op_id = uuid4()
        self.opening = M.objects.create(user=self.user, investment=self.source_inv, date=date(2026, 11, 11), type='aporte',
                                        amount=1000, quantity=1000, operation_id=op_id)
        self.old_debit = M.objects.create(user=self.user, investment=self.legacy, date=date(2026, 11, 11), type='resgate',
                                          amount=1000, operation_id=op_id)
        self.buy_op.movements.set([self.opening, self.old_debit])
        self.buy_op.cash_evidence.add(self.buy_cash)
        self.partial_cash = self.cash('CREDIT', 403, '2026-11-10T14:30:00Z', 'Resgate - CDB Inter')
        self.partial = self.event('SELL', '2026-11-10T00:00:00Z', 400, 404, 403, {'incomeTax': 1})
        self.partial_op = ReconciledInvestmentOperation.objects.create(event=self.partial, kind='sell', state='linked', evidence='Resgate antigo')
        op_id = uuid4()
        self.old_sale = M.objects.create(user=self.user, investment=self.legacy, date=date(2026, 11, 10),
                                         type='resgate', amount=403, operation_id=op_id)
        wallet_credit = M.objects.create(user=self.user, investment=self.wallet, date=date(2026, 11, 10),
                                          type='aporte', amount=403, operation_id=op_id)
        M.objects.create(user=self.user, investment=self.wallet, date=date(2026, 11, 10), type='resgate', amount=403)
        self.partial_op.movements.set([self.old_sale, wallet_credit])
        self.partial_op.cash_evidence.add(self.partial_cash)
        self.stale = self.snapshot('2026-11-10T14:00:00Z', date(2026, 11, 11), 1002, 1000)
        self.plain = M.objects.create(user=self.user, investment=self.source_inv, date=date(2026, 11, 11),
                                      type='atualizacao', current_value=1002)
        M.objects.create(user=self.user, investment=self.legacy, date=date(2026, 11, 11), type='atualizacao', current_value=0)
        self.snapshot('2026-11-12T14:00:00Z', date(2026, 11, 12), 602, 600)
        self.closing = self.snapshot('2026-11-16T14:00:00Z', date(2026, 11, 16), 0, 0)
        self.credit = self.cash('CREDIT', 606, '2026-11-16T00:00:03Z', 'Resgate - CDB Inter')
        self.debit = self.cash('DEBIT', -606, '2026-11-16T00:01:36Z', 'Compra - Criptomoedas')
        # Old custody intentionally uses native currency; the new cost-basis asset must stay separate.
        btc = Asset.objects.create(user=self.user, description='Bitcoin', symbol='BTC', asset_type='crypto', currency='BTC')
        exchange = Broker.objects.create(user=self.user, description='Mercado Bitcoin', kind='exchange')
        self.old_btc = Investment.objects.create(user=self.user, asset=btc, broker=exchange,
                                                description='Bitcoin (Mercado Bitcoin)', start_date=date(2020, 1, 1))
        M.objects.create(user=self.user, investment=self.old_btc, date=date(2020, 1, 1), type='aporte', amount=100, quantity='.001')

    def cash(self, kind, value, when, description):
        return InvestmentCashEvidence.objects.create(connection=self.connection, external_id=str(uuid4()), account_id=self.account,
            facts={'type': kind, 'amount': value, 'date': when, 'description': description, 'status': 'POSTED', 'currencyCode': 'BRL'})

    def event(self, kind, when, quantity, gross, net, expenses=None):
        event = InvestmentEvent.objects.create(connection=self.connection, external_id=str(uuid4()), state='linked', revision=1,
            facts={'type': kind, 'date': when, 'quantity': quantity, 'amount': gross, 'netAmount': net, 'expenses': expenses})
        event.investments.add(self.source)
        return event

    def snapshot(self, reference, day, value, quantity):
        m = M.objects.create(user=self.user, investment=self.source_inv, date=day, type='atualizacao', current_value=value, quantity=quantity)
        return InvestmentSnapshot.objects.create(external=self.source, reference_at=parse_datetime(reference), fingerprint=str(uuid4()),
            facts={'balance': str(value), 'quantity': str(quantity)}, movement=m)

    def apply(self, **kwargs):
        return register_purchase(kwargs.pop('user', self.user), self.debit.pk, kwargs.pop('revision', 1),
            self.source.pk, self.credit.pk, kwargs.pop('symbol', 'BTC'), kwargs.pop('quantity', '.002'), 'Dados confirmados pelo usuário')

    def test_reconstructs_cost_and_registers_resgate_to_bitcoin_without_double_counting(self):
        self.assertEqual(purchase_options(self.debit)[0]['principal'], '600.00')
        old_btc = Positions.get_position(self.old_btc)
        trade = self.apply()
        source = Positions.get_position(self.source_inv)
        for key in ['value', 'quantity', 'remaining_principal', 'unwithdrawn_income']:
            self.assertEqual(source[key], 0, key)
        target = Positions.get_position(trade.investment)
        self.assertEqual(target['value'], 606)
        self.assertEqual(target['quantity'], Decimal('.002'))
        self.assertEqual(Positions.get_position(self.wallet)['value'], 0)
        self.assertEqual(Positions.get_position(self.legacy)['value'], 0)
        self.assertEqual(Positions.get_position(self.old_btc)['value'], old_btc['value'])
        self.assertEqual(Positions.get_position(self.old_btc)['quantity'], old_btc['quantity'])
        self.assertNotEqual(trade.investment.asset_id, self.old_btc.asset_id)
        self.assertEqual(trade.investment.asset.currency, 'BRL')
        self.opening.refresh_from_db()
        self.assertEqual(self.opening.date, date(2026, 11, 6))
        self.old_sale.refresh_from_db()
        self.assertEqual(self.old_sale.investment_id, self.source_inv.pk)
        self.assertEqual(self.old_sale.redemption_principal, 400)
        self.stale.refresh_from_db()
        self.assertEqual(self.stale.facts['quantity'], '1000')
        self.stale.movement.refresh_from_db()
        self.assertFalse(self.stale.movement.affects_value)
        self.assertIsNone(self.stale.movement.quantity)
        self.assertTrue(trade.journal['changes'])
        self.assertEqual(trade.reviews.count(), 2)
        income = sum(M.objects.filter(user=self.user, type='rendimento').values_list('amount', flat=True))
        costs = sum(M.objects.filter(user=self.user, type='custo').values_list('amount', flat=True))
        self.assertEqual(income - costs, 9)

    def test_retry_is_idempotent_and_changed_inputs_are_not_silently_accepted(self):
        first = self.apply()
        count = M.objects.count()
        self.assertEqual(self.apply().pk, first.pk)
        self.assertEqual(M.objects.count(), count)
        with self.assertRaises(ValidationError):
            self.apply(quantity='.003')
        with self.assertRaises(ValidationError):
            self.apply(revision=2)

    def test_invalid_owner_revision_or_quantity_does_not_create_partial_data(self):
        before = list(M.objects.order_by('pk').values())
        for quantity in ['0', '-1', 'NaN', '.000000001']:
            with self.assertRaises(ValidationError):
                self.apply(quantity=quantity)
        with self.assertRaises(InvestmentCashEvidence.DoesNotExist):
            self.apply(user=self.other)
        with self.assertRaises(ValidationError):
            self.apply(revision=2)
        self.assertEqual(list(M.objects.order_by('pk').values()), before)
        self.assertFalse(InvestmentBankTrade.objects.exists())

    def test_ambiguous_credit_or_unproven_cost_stays_pending(self):
        extra = self.cash('CREDIT', 606, '2026-11-16T00:00:04Z', 'Resgate - CDB Inter')
        self.assertEqual(purchase_options(self.debit), [])
        extra.delete()
        self.buy_op.cash_evidence.clear()
        self.assertEqual(purchase_options(self.debit), [])
        with self.assertRaises(ValidationError):
            self.apply()

    def test_failure_after_corrections_rolls_back_ledger_and_new_asset(self):
        before = list(M.objects.order_by('pk').values())
        with patch.object(Service, 'validate_balances', side_effect=ValidationError('Falha de validação')):
            with self.assertRaises(ValidationError):
                self.apply()
        self.assertEqual(list(M.objects.order_by('pk').values()), before)
        self.assertFalse(InvestmentBankTrade.objects.exists())
        self.assertFalse(Asset.objects.filter(user=self.user, symbol='BTC', currency='BRL').exists())
        self.partial_op.refresh_from_db()
        self.assertEqual(self.partial_op.state, 'linked')

    def test_recorded_movements_are_protected_and_api_requires_post(self):
        trade = self.apply()
        movement = trade.reviews.get(cash=self.debit).movements.get(type='aporte')
        with self.assertRaises(ValidationError):
            Service.delete(movement)
        request = RequestFactory().get('/')
        request.user = self.user
        self.assertEqual(bank_purchase(request, self.debit.pk).status_code, 405)

    def test_later_provider_event_adopts_the_recorded_redemption_without_double_counting(self):
        from bank_sync.event_import import import_events
        trade = self.apply()
        event = self.event('SELL', '2026-11-16T00:00:00Z', 600, 609, 606, {'incomeTax': 3})
        event.state = 'new'
        event.last_seen_job = InvestmentHistoryJob.objects.filter(connection=self.connection).latest('id')
        event.save()
        before = list(M.objects.order_by('pk').values())
        self.assertEqual(import_events(self.connection)['adopted'], [event.pk])
        self.assertEqual(list(M.objects.order_by('pk').values()), before)
        self.assertTrue(event.operation.cash_evidence.filter(pk=self.credit.pk).exists())
        self.assertEqual(import_events(self.connection), {'applied': [], 'adopted': []})

    def test_provider_final_event_is_saved_with_the_financial_records_when_already_available(self):
        event = self.event('SELL', '2026-11-16T00:00:00Z', 600, 609, 606, {'incomeTax': 3})
        event.state = 'new'
        event.save()
        trade = self.apply()
        event.refresh_from_db()
        self.assertEqual(event.state, 'applied')
        self.assertTrue(event.operation.cash_evidence.filter(pk=self.credit.pk).exists())
        self.assertEqual(Positions.get_position(trade.investment)['value'], 606)

    def test_quote_quantity_mismatch_or_another_closed_holding_prevents_inferred_funding(self):
        self.snapshot('2026-11-15T14:00:00Z', date(2026, 11, 15), 500, 500)
        self.assertEqual(purchase_options(self.debit), [])
        self.source.snapshots.filter(reference_at__date=date(2026, 11, 15)).delete()
        # Remove the derived movement as well; no production/manual financial record is changed here.
        M.objects.filter(investment=self.source_inv, date=date(2026, 11, 15)).delete()
        ExternalInvestment.objects.create(connection=self.connection, external_id=uuid4(),
            facts={'name': 'Outro CDB', 'status': 'TOTAL_WITHDRAWAL', 'date': '2026-11-16T14:00:00Z'})
        self.assertEqual(purchase_options(self.debit), [])

    def test_source_revision_preserves_money_and_requires_explicit_conflict_review(self):
        from bank_sync.bank_trades import flag_bank_trade_conflicts, keep_bank_trade
        from bank_sync.cash_reviews import bank_rows
        trade = self.apply()
        before = list(M.objects.order_by('pk').values())
        self.debit.revision = 2
        self.debit.facts['amount'] = -607
        self.debit.save()
        flag_bank_trade_conflicts(self.connection)
        trade.refresh_from_db()
        self.assertEqual(trade.state, 'conflict')
        self.assertTrue(bank_rows(self.user).filter(pk=self.debit.pk, reviewed=False).exists())
        self.assertEqual(list(M.objects.order_by('pk').values()), before)
        with self.assertRaises(ValidationError):
            keep_bank_trade(self.user, self.debit.pk, 2, '')
        keep_bank_trade(self.user, self.debit.pk, 2, 'Conferi o comprovante original; manter o registro local de 606.')
        flag_bank_trade_conflicts(self.connection)
        trade.refresh_from_db()
        self.assertEqual(trade.state, 'applied')
        self.assertEqual(list(M.objects.order_by('pk').values()), before)
        self.assertEqual(trade.reviews.filter(cash=self.debit).count(), 2)
