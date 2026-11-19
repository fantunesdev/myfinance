from datetime import date
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import TestCase, RequestFactory

from bank_sync.cash_reviews import bank_rows, candidates, review_cash
from bank_sync.event_views import bank_review, event_list
from bank_sync.models import BankConnection, InvestmentCashEvidence
from investments.models import Asset, Investment, InvestmentTransaction as Movement
from investments.services.transaction import InvestmentTransactionService as Service
from login.models import User
import json


class CashReviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='cash-review', email='cash-review@example.invalid')
        self.other = User.objects.create(username='cash-other', email='cash-other@example.invalid')
        self.connection = BankConnection.objects.create(user=self.user, item_id=uuid4())
        wallet = Service.get_or_create_default_wallet(self.user)
        asset = Asset.objects.create(user=self.user, description='CDB', asset_type='fixed_income')
        self.investment = Investment.objects.create(
            user=self.user, asset=asset, broker=wallet.broker,
            description='CDB', start_date=date(2020, 1, 1),
        )
        self.movement = Movement.objects.create(
            user=self.user, investment=self.investment, date=date(2026, 11, 10), type='resgate', amount=100,
        )
        self.cash = InvestmentCashEvidence.objects.create(
            connection=self.connection, external_id=str(uuid4()), account_id=uuid4(),
            facts={'date': '2026-11-10T00:00:00Z', 'amount': 100, 'type': 'CREDIT',
                   'description': 'Resgate - CDB', 'status': 'POSTED', 'currencyCode': 'BRL'},
        )

    def review(self, **kwargs):
        return review_cash(self.user, self.cash.pk, kwargs.pop('revision', 1),
                           kwargs.pop('action', 'link'), kwargs.pop('movement_id', self.movement.pk),
                           kwargs.pop('evidence', 'Resgate já registrado no CDB.'))

    def test_link_preserves_money_and_exposes_readonly_review_in_history(self):
        before = list(Movement.objects.values())
        review = self.review()
        self.assertEqual(list(review.movements.all()), [self.movement])
        self.assertEqual(list(Movement.objects.values()), before)
        self.assertFalse(bank_rows(self.user).filter(reviewed=False).exists())
        request = RequestFactory().get('/', {'state': 'bank_history'})
        request.user = self.user
        data = json.loads(event_list(request).content)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['summary']['bank_pending'], 0)
        self.assertEqual(data['bank_entries'][0]['review']['evidence'], review.evidence)
        self.assertEqual(data['bank_entries'][0]['candidates'][0]['id'], self.movement.pk)
        with self.assertRaises(ValidationError):
            self.review()
        with self.assertRaises(ValidationError):
            Service.delete(self.movement)

    def test_covered_requires_explicit_evidence_and_never_changes_balances(self):
        with self.assertRaises(ValidationError):
            self.review(action='covered', evidence=' ')
        before = list(Movement.objects.values())
        review = self.review(action='covered', evidence='Incluído na reconstrução histórica, lote documentado.')
        self.assertFalse(review.movements.exists())
        self.assertEqual(list(Movement.objects.values()), before)

    def test_changed_source_revision_returns_to_pending_and_preserves_old_review(self):
        old = self.review()
        self.cash.revision = 2
        self.cash.facts['amount'] = 101
        self.cash.save()
        self.assertTrue(bank_rows(self.user).filter(reviewed=False).exists())
        self.assertEqual(old.revision, 1)
        self.assertTrue(old.movements.filter(pk=self.movement.pk).exists())
        with self.assertRaises(ValidationError):
            self.review(revision=1)
        with self.assertRaises(ValidationError):
            self.review(revision=2)

    def test_wrong_owner_amount_direction_or_date_cannot_be_linked(self):
        for changes in [dict(user=self.other), dict(amount=99), dict(type='aporte'),
                        dict(date=date(2026, 9, 1))]:
            self.movement.refresh_from_db()
            original = {field: getattr(self.movement, field) for field in changes}
            Movement.objects.filter(pk=self.movement.pk).update(**changes)
            with self.assertRaises(ValidationError):
                self.review()
            Movement.objects.filter(pk=self.movement.pk).update(**original)
        with self.assertRaises(InvestmentCashEvidence.DoesNotExist):
            review_cash(self.other, self.cash.pk, 1, 'covered', evidence='Outro usuário')

    def test_one_local_movement_cannot_explain_two_bank_entries(self):
        self.review()
        self.cash.pk = None
        self.cash.external_id = str(uuid4())
        self.cash.save()
        with self.assertRaises(ValidationError):
            self.review()

    def test_wallet_and_unposted_bank_rows_are_not_eligible(self):
        self.movement.investment = Service.get_or_create_default_wallet(self.user)
        self.movement.save()
        self.assertFalse(candidates(self.user, self.cash).exists())
        self.cash.facts['status'] = 'PENDING'
        self.cash.save()
        with self.assertRaises(ValidationError):
            self.review(action='covered')

    def test_api_requires_post_and_validates_revision(self):
        request = RequestFactory().get('/')
        request.user = self.user
        self.assertEqual(bank_review(request, self.cash.pk).status_code, 405)
        request = RequestFactory().post('/', json.dumps({'revision': 2, 'action': 'covered', 'evidence': 'teste'}),
                                        content_type='application/json')
        request.user = self.user
        self.assertEqual(bank_review(request, self.cash.pk).status_code, 400)
