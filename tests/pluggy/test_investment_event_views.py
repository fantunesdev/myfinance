import json
from datetime import date
from uuid import uuid4

from django.test import RequestFactory, TestCase
from django.utils import timezone

from bank_sync.event_views import event_list
from bank_sync.models import (
    BankConnection,
    ExternalInvestment,
    InvestmentCashEvidence,
    InvestmentEvent,
    InvestmentHistoryJob,
    InvestmentOperationEvent,
    ReconciledInvestmentOperation,
)
from investments.models import Asset, Investment, InvestmentTransaction
from investments.services.transaction import InvestmentTransactionService
from login.models import User


class InvestmentEventListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='event-view', email='event-view@example.invalid')
        self.other = User.objects.create(username='event-other', email='event-other@example.invalid')
        self.connection = BankConnection.objects.create(user=self.user, item_id=uuid4())
        self.other_connection = BankConnection.objects.create(user=self.other, item_id=uuid4())
        self.wallet = InvestmentTransactionService.get_or_create_default_wallet(self.user)
        asset = Asset.objects.create(
            user=self.user, description='Ação de teste', symbol='TEST3', asset_type='variable_income'
        )
        self.investment = Investment.objects.create(
            user=self.user,
            asset=asset,
            broker=self.wallet.broker,
            description='Ação TEST3',
            start_date=date(2020, 1, 1),
        )
        self.source = ExternalInvestment.objects.create(
            connection=self.connection, external_id=uuid4(), investment=self.investment, facts={'name': 'TEST3'}
        )
        self.job = InvestmentHistoryJob.objects.create(
            connection=self.connection, state='succeeded', finished_at=timezone.now()
        )

    def event(self, state='historical', **overrides):
        event = InvestmentEvent.objects.create(
            connection=self.connection,
            external_id=str(uuid4()),
            state=state,
            last_seen_job=self.job,
            facts={'date': '2026-11-01T00:00:00Z', 'type': 'INTEREST', 'amount': 10, 'netAmount': 10, **overrides},
        )
        event.investments.add(self.source)
        return event

    def get(self, **params):
        request = RequestFactory().get('/investimentos/conciliacao/eventos/', params)
        request.user = self.user
        response = event_list(request)
        return response.status_code, json.loads(response.content)

    def test_default_shows_only_pending_and_counts_resolved_separately(self):
        pending = self.event()
        self.event('applied')
        self.event('linked')
        self.event('ignored')
        self.event('conflict')
        InvestmentEvent.objects.create(
            connection=self.other_connection,
            external_id=str(uuid4()),
            state='new',
            facts={'date': '2026-11-01T00:00:00Z'},
        )
        status, data = self.get()
        self.assertEqual(status, 200)
        self.assertEqual(data['filter'], 'pending')
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['summary'], {'pending': 2, 'resolved': 3, 'total': 5})
        self.assertEqual({e['state'] for e in data['events']}, {'historical', 'conflict'})
        self.assertIn(pending.pk, [e['id'] for e in data['events']])

    def test_no_pending_does_not_return_the_first_page_of_history(self):
        for unused in range(21):
            self.event('applied')
        status, data = self.get()
        self.assertEqual((status, data['count'], data['events']), (200, 0, []))
        self.assertEqual(data['summary']['resolved'], 21)
        self.assertEqual(data['credits'], [])
        status, history = self.get(state='resolved')
        self.assertEqual((status, history['count'], len(history['events']), history['pages']), (200, 21, 20, 2))
        status, last = self.get(state='resolved', page=999)
        self.assertEqual((status, last['page'], len(last['events'])), (200, 2, 1))

    def test_resolved_provento_uses_confirmed_classification_and_readonly_evidence(self):
        event = self.event('applied', type='SELL', description='Rendimento')
        operation = ReconciledInvestmentOperation.objects.create(
            event=event, kind='income', state='applied', evidence='Crédito comprovado'
        )
        movement = InvestmentTransaction.objects.create(
            user=self.user,
            investment=self.investment,
            date=date(2026, 11, 1),
            type='rendimento',
            amount=10,
            affects_value=False,
        )
        operation.movements.add(movement)
        cash = InvestmentCashEvidence.objects.create(
            connection=self.connection,
            external_id=str(uuid4()),
            account_id=uuid4(),
            facts={'date': '2026-11-01T00:00:00Z', 'amount': 10, 'type': 'CREDIT', 'description': 'Dividendos TEST3'},
        )
        operation.cash_evidence.add(cash)
        status, data = self.get(state='resolved')
        row = data['events'][0]
        self.assertEqual((status, row['kind'], row['source_kind']), (200, 'income', 'ambiguous'))
        self.assertEqual(row['operation']['id'], operation.pk)
        self.assertEqual([m['id'] for m in row['matched_movements']], [movement.pk])
        self.assertEqual(row['settlements'][0]['facts']['amount'], 10)
        self.assertEqual(row['candidates'], [])
        self.assertEqual(row['cash_candidates'], [])
        self.assertEqual(data['credits'], [])

    def test_group_member_gets_its_operation_and_confirmed_purchase_kind(self):
        parent = self.event('linked', type='BUY')
        child = self.event('linked', type='BUY')
        operation = ReconciledInvestmentOperation.objects.create(
            event=parent, kind='purchase_group', state='linked', evidence='Liquidação agrupada'
        )
        InvestmentOperationEvent.objects.create(event=child, operation=operation)
        status, data = self.get(state='resolved')
        row = next(e for e in data['events'] if e['id'] == child.pk)
        self.assertEqual(status, 200)
        self.assertEqual(row['kind'], 'buy')
        self.assertEqual(row['operation']['id'], operation.pk)
        self.assertEqual(row['operation']['event_count'], 2)

    def test_history_evidence_never_leaks_foreign_user_records(self):
        event = self.event('applied')
        operation = ReconciledInvestmentOperation.objects.create(
            event=event, kind='income', state='applied', evidence='Conferido'
        )
        foreign_wallet = InvestmentTransactionService.get_or_create_default_wallet(self.other)
        foreign = InvestmentTransaction.objects.create(
            user=self.other,
            investment=foreign_wallet,
            date=date(2026, 11, 1),
            type='aporte',
            amount=99,
            notes='PRIVATE',
        )
        foreign_cash = InvestmentCashEvidence.objects.create(
            connection=self.other_connection,
            external_id=str(uuid4()),
            account_id=uuid4(),
            facts={'description': 'PRIVATE'},
        )
        operation.movements.add(foreign)
        operation.cash_evidence.add(foreign_cash)
        status, data = self.get(state='resolved')
        self.assertEqual(status, 200)
        self.assertEqual(data['events'][0]['matched_movements'], [])
        self.assertEqual(data['events'][0]['settlements'], [])
        self.assertNotIn('PRIVATE', json.dumps(data))

    def test_foreign_mapping_is_not_exposed_as_a_candidate_or_title(self):
        foreign_wallet = InvestmentTransactionService.get_or_create_default_wallet(self.other)
        foreign_wallet.description = 'PRIVATE-TITLE'
        foreign_wallet.save()
        self.source.investment = foreign_wallet
        self.source.save()
        self.event()
        status, data = self.get()
        self.assertEqual(status, 200)
        self.assertFalse(data['events'][0]['mapped'])
        self.assertEqual(data['events'][0]['candidates'], [])
        self.assertNotIn('PRIVATE-TITLE', json.dumps(data))

    def test_bad_filter_returns_validation_error(self):
        status, unused = self.get(state='not-a-state')
        self.assertEqual(status, 400)

    def test_default_empty_filter_and_explicit_all_have_distinct_meanings(self):
        self.event('applied')
        self.assertEqual(self.get(state='')[1]['count'], 0)
        self.assertEqual(self.get(state='all')[1]['count'], 1)

    def test_new_purchase_only_offers_usable_debits_and_purchase_records(self):
        self.event('new', type='BUY')
        InvestmentTransaction.objects.create(
            user=self.user, investment=self.investment, date=date(2026, 11, 1), type='atualizacao', current_value=500
        )
        for direction, status, currency in [
            ('CREDIT', 'POSTED', 'BRL'),
            ('DEBIT', 'PENDING', 'BRL'),
            ('DEBIT', 'POSTED', 'USD'),
            ('DEBIT', 'POSTED', 'BRL'),
        ]:
            InvestmentCashEvidence.objects.create(
                connection=self.connection,
                external_id=str(uuid4()),
                account_id=uuid4(),
                facts={
                    'date': '2026-11-01T00:00:00Z',
                    'type': direction,
                    'status': status,
                    'currencyCode': currency,
                    'amount': 10,
                },
            )
        status, data = self.get()
        row = data['events'][0]
        self.assertEqual(status, 200)
        self.assertEqual(row['candidates'], [])
        self.assertEqual(len(row['cash_candidates']), 1)
        self.assertEqual(row['cash_candidates'][0]['facts']['type'], 'DEBIT')
        self.assertEqual(row['cash_candidates'][0]['facts']['status'], 'POSTED')
        self.assertEqual(row['cash_candidates'][0]['facts']['currencyCode'], 'BRL')
