import json
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from types import SimpleNamespace
from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.test import RequestFactory, TestCase
from django.utils import timezone
from django.utils.functional import SimpleLazyObject

from bank_sync import views
from bank_sync.models import (
    BankConnection,
    ExternalAccount,
    ExternalBill,
    ExternalCardIdentifier,
    ExternalTransaction,
    ProjectedInstallment,
    SyncRun,
)
from bank_sync.services import confirm, map_account, normalize, sync_connection
from login.models import User
from statement.models import (
    Card,
    CardNumber,
    Category,
    Currency,
    Flag,
    Subcategory,
    Transaction,
)


class PluggyIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="pluggy-owner", email="owner@test.invalid")
        self.other = User.objects.create(username="other-owner", email="other@test.invalid")
        self.connection = BankConnection.objects.create(user=self.user, item_id=uuid4())
        flag = Flag.objects.create(description="Test")
        self.card = Card.objects.create(
            user=self.user, flag=flag, description="Test card", closing_day=3, expiration_day=10
        )
        self.number = CardNumber.objects.create(card=self.card, number="1234", name="Primary")
        self.category = Category.objects.create(type="saida", description="Test expense")
        self.subcategory = Subcategory.objects.create(category=self.category, description="Test subcategory")
        Currency.objects.get_or_create(pk="BRL", defaults={"description": "Real", "symbol": "R$"})
        self.account_id, self.bill_id, self.tx_id = str(uuid4()), str(uuid4()), str(uuid4())
        self.account = {
            "id": self.account_id,
            "type": "CREDIT",
            "subtype": "CREDIT_CARD",
            "name": "Test card",
            "currencyCode": "BRL",
            "balance": 200,
        }
        self.bill = {
            "id": self.bill_id,
            "dueDate": "2026-11-10",
            "billClosingDate": "2026-11-03",
            "totalAmount": 100,
            "totalAmountCurrencyCode": "BRL",
        }
        self.raw = {
            "id": self.tx_id,
            "accountId": self.account_id,
            "amount": 100,
            "currencyCode": "BRL",
            "date": "2026-10-20T03:00:00Z",
            "description": "Test merchant",
            "status": "POSTED",
            "type": "DEBIT",
            "operationType": "PAGAMENTO",
            "creditCardMetadata": {
                "cardNumber": "1234",
                "paymentType": "INSTALLMENT",
                "purchaseDate": "2026-09-20",
                "installmentNumber": 2,
                "totalInstallments": 3,
                "billId": self.bill_id,
            },
        }
        self.factory = RequestFactory()

    def reader(self, rows=None, bills=None):
        reader = Mock()
        reader.request.return_value = {"status": "UPDATED", "executionStatus": "SUCCESS"}
        reader.numbered.side_effect = [[deepcopy(self.account)], deepcopy(bills if bills is not None else [self.bill])]
        reader.transactions.return_value = deepcopy(rows if rows is not None else [self.raw])
        return reader

    def ingest(self, rows=None, bills=None):
        sync_connection(self.connection, self.reader(rows, bills))
        return ExternalTransaction.objects.get(external_id=self.tx_id)

    def mapped(self):
        row = self.ingest()
        map_account(self.user, row.account_id, self.card.pk, {})
        row.refresh_from_db()
        return row

    def create_data(self, **kwargs):
        return {"category_id": self.category.pk, "subcategory_id": self.subcategory.pk, **kwargs}

    def local(self, **kwargs):
        return Transaction.objects.create(
            user=self.user,
            card=self.card,
            card_number=self.number,
            category=self.category,
            subcategory=self.subcategory,
            value=100,
            posted_date=date(2026, 9, 20),
            payment_date=date(2026, 11, 10),
            description="Manual test",
            currency_id="BRL",
            **kwargs
        )

    def test_sync_is_idempotent_and_does_not_create_financial_rows(self):
        self.ingest()
        self.ingest()
        self.assertEqual(ExternalTransaction.objects.count(), 1)
        self.assertEqual(ExternalBill.objects.count(), 1)
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(SyncRun.objects.filter(state="succeeded").count(), 2)

    def test_confirmation_accepts_lazy_session_user(self):
        row = self.mapped()
        result = confirm(SimpleLazyObject(lambda: self.user), row.pk, 1, "create", self.create_data())
        self.assertEqual(result.transaction.user_id, self.user.pk)

    def test_unlink_preserves_the_financial_entry(self):
        row = self.mapped()
        confirmed = confirm(self.user, row.pk, 1, "create", self.create_data())
        target_id = confirmed.transaction_id
        result = confirm(self.user, row.pk, 1, "unlink", {})
        self.assertEqual(result.state, "new")
        self.assertIsNone(result.transaction_id)
        self.assertTrue(Transaction.objects.filter(pk=target_id).exists())

    def test_editing_imported_installment_does_not_regenerate_legacy_plan(self):
        from statement.views.core.transaction import TransactionView
        from unittest.mock import patch

        row = self.mapped()
        target = confirm(self.user, row.pk, 1, "create", self.create_data()).transaction
        view = TransactionView()
        view._context = "update"
        with patch("statement.views.core.transaction.InstallmentService.create") as create:
            view._custom_actions(None, None, target)
            create.assert_not_called()
        self.assertIsNone(target.installment_id)

    def test_failed_fetch_keeps_previous_snapshot_and_releases_lease(self):
        row = self.ingest()
        reader = self.reader()
        reader.transactions.side_effect = RuntimeError("private response not safe to log")
        with self.assertRaises(RuntimeError):
            sync_connection(self.connection, reader)
        row.refresh_from_db()
        self.assertEqual(row.revision, 1)
        self.connection.refresh_from_db()
        self.assertIsNone(self.connection.lease_until)
        self.assertNotIn("private", SyncRun.objects.latest("id").message)

    def test_active_lease_blocks_parallel_sync(self):
        self.connection.lease_until = timezone.now() + timedelta(minutes=1)
        self.connection.save()
        reader = self.reader()
        with self.assertRaises(ValidationError):
            sync_connection(self.connection, reader)
        reader.authenticate.assert_not_called()

    def test_expired_authorization_does_not_erase_history(self):
        self.ingest()
        reader = self.reader()
        reader.request.return_value = {"status": "UPDATED", "consentExpiresAt": "2020-01-01T00:00:00Z"}
        with self.assertRaises(ValidationError):
            sync_connection(self.connection, reader)
        self.assertEqual(ExternalTransaction.objects.count(), 1)

    def test_unknown_or_ambiguous_card_blocks_confirmation(self):
        row = self.ingest()
        with self.assertRaises(ValidationError):
            confirm(self.user, row.pk, 1, "create", self.create_data())
        CardNumber.objects.create(card=self.card, number="****1234")
        map_account(self.user, row.account_id, self.card.pk, {})
        self.assertIsNone(row.account.identifiers.get().card_number_id)
        with self.assertRaises(ValidationError):
            confirm(self.user, row.pk, 1, "create", self.create_data())

    def test_other_owner_cannot_map_or_confirm(self):
        row = self.mapped()
        with self.assertRaises(ObjectDoesNotExist):
            confirm(self.other, row.pk, 1, "ignore", {})
        with self.assertRaises(ObjectDoesNotExist):
            map_account(self.other, row.account_id, self.card.pk, {})

    def test_ignore_survives_sync(self):
        row = self.ingest()
        confirm(self.user, row.pk, 1, "ignore", {})
        self.ingest()
        row.refresh_from_db()
        self.assertEqual(row.state, "ignored")
        self.assertFalse(Transaction.objects.exists())

    def test_confirm_uses_bill_due_date_and_does_not_divide_installment_amount(self):
        row = self.mapped()
        result = confirm(self.user, row.pk, 1, "create", self.create_data())
        target = result.transaction
        self.assertEqual(target.payment_date, date(2026, 11, 10))
        self.assertEqual(target.posted_date, date(2026, 9, 20))
        self.assertEqual(target.value, 100)
        self.assertEqual(target.paid, 2)
        self.assertEqual(target.installments_number, 3)
        self.assertFalse(target.effected)
        confirm(self.user, row.pk, 1, "create", self.create_data())
        self.assertEqual(Transaction.objects.count(), 1)

    def test_source_changes_flag_conflict_and_preserve_local_edits(self):
        row = self.mapped()
        local = confirm(self.user, row.pk, 1, "create", self.create_data(description="My description")).transaction
        self.raw["amount"] = 101
        self.ingest()
        row.refresh_from_db()
        local.refresh_from_db()
        self.assertEqual((row.state, row.revision), ("conflict", 2))
        self.assertEqual((local.value, local.description), (100, "My description"))
        with self.assertRaises(ValidationError):
            confirm(self.user, row.pk, 1, "keep", {})
        confirm(self.user, row.pk, 2, "keep", {})
        self.assertEqual(Transaction.objects.count(), 1)

    def test_bill_due_date_change_flags_conflict_without_touching_transaction(self):
        row = self.mapped()
        local = confirm(self.user, row.pk, 1, "create", self.create_data()).transaction
        self.bill["dueDate"] = "2026-11-11"
        self.ingest()
        row.refresh_from_db()
        local.refresh_from_db()
        self.assertEqual(row.state, "conflict")
        self.assertEqual(local.payment_date, date(2026, 11, 10))

    def test_manual_or_notification_match_requires_explicit_decision(self):
        row = self.mapped()
        local = self.local(source_type="notification")
        with self.assertRaises(ValidationError):
            confirm(self.user, row.pk, 1, "create", self.create_data())
        confirm(self.user, row.pk, 1, "link", {"transaction_id": local.pk})
        self.assertEqual(Transaction.objects.count(), 1)

    def installment_plan(self):
        from dateutil.relativedelta import relativedelta

        anchor = self.mapped()
        rows, locals_ = {}, {}
        for sequence in (1, 2, 3):
            due = date(2026, 11, 10) + relativedelta(months=sequence - 2)
            if sequence == 2:
                source = anchor
            else:
                bill_id = str(uuid4())
                ExternalBill.objects.create(
                    account=anchor.account, external_id=bill_id, due_date=due, total=100, currency="BRL"
                )
                facts = {**anchor.facts, "number": sequence, "bill_id": bill_id}
                source = ExternalTransaction.objects.create(
                    account=anchor.account, external_id=uuid4(), facts=facts, fingerprint=anchor.fingerprint
                )
            local = self.local(paid=sequence, installments_number=3, source_type="notification")
            Transaction.objects.filter(pk=local.pk).update(payment_date=due)
            local.refresh_from_db()
            rows[sequence], locals_[sequence] = source, local
        return rows, locals_

    def test_link_reconciles_entire_installment_plan_across_bills(self):
        rows, locals_ = self.installment_plan()
        before = list(Transaction.objects.order_by("pk").values())
        result = confirm(self.user, rows[2].pk, rows[2].revision, "link", {"transaction_id": locals_[2].pk})
        self.assertEqual(result.reconciled_count, 3)
        self.assertEqual(result.remaining_installments, 0)
        for sequence, source in rows.items():
            source.refresh_from_db()
            self.assertEqual((source.state, source.transaction_id), ("linked", locals_[sequence].pk))
        self.assertEqual(list(Transaction.objects.order_by("pk").values()), before)
        confirm(self.user, rows[2].pk, rows[2].revision, "link", {"transaction_id": locals_[2].pk})
        self.assertEqual(Transaction.objects.count(), 3)

    def test_group_reconciliation_leaves_ambiguous_or_missing_candidates_pending(self):
        rows, locals_ = self.installment_plan()
        duplicate = self.local(paid=1, installments_number=3)
        Transaction.objects.filter(pk=duplicate.pk).update(payment_date=locals_[1].payment_date)
        locals_[3].delete()
        result = confirm(self.user, rows[2].pk, rows[2].revision, "link", {"transaction_id": locals_[2].pk})
        self.assertEqual((result.reconciled_count, result.remaining_installments), (1, 2))
        for sequence in (1, 3):
            rows[sequence].refresh_from_db()
            self.assertEqual(rows[sequence].state, "new")

    def test_group_reconciliation_does_not_merge_different_card_or_purchase(self):
        from bank_sync.services import plan_fingerprint

        rows, locals_ = self.installment_plan()
        facts = {**rows[1].facts, "last_four": "9999"}
        ExternalTransaction.objects.filter(pk=rows[1].pk).update(facts=facts, fingerprint=plan_fingerprint(facts))
        facts = {**rows[3].facts, "purchase_date": "2026-09-21"}
        ExternalTransaction.objects.filter(pk=rows[3].pk).update(facts=facts, fingerprint=plan_fingerprint(facts))
        result = confirm(self.user, rows[2].pk, rows[2].revision, "link", {"transaction_id": locals_[2].pk})
        self.assertEqual(result.reconciled_count, 1)
        self.assertEqual(ExternalTransaction.objects.filter(state="new").count(), 2)

    def test_duplicate_source_installment_numbers_do_not_merge_purchases(self):
        rows, locals_ = self.installment_plan()
        ExternalTransaction.objects.create(
            account=rows[2].account, external_id=uuid4(), facts=rows[2].facts, fingerprint=rows[2].fingerprint
        )
        result = confirm(self.user, rows[2].pk, rows[2].revision, "link", {"transaction_id": locals_[2].pk})
        self.assertEqual((result.reconciled_count, result.remaining_installments), (1, 3))

    def test_identical_legitimate_purchase_can_be_confirmed_distinct(self):
        row = self.mapped()
        self.local()
        confirm(self.user, row.pk, 1, "create", self.create_data(distinct_purchase=True))
        self.assertEqual(Transaction.objects.count(), 2)

    def test_projection_is_estimated_then_linked_without_extra_expense(self):
        row = self.mapped()
        confirm(self.user, row.pk, 1, "create", self.create_data(project_remaining=True))
        predicted = ProjectedInstallment.objects.get()
        self.assertEqual(predicted.number, 3)
        self.assertEqual(predicted.transaction.payment_date, date(2026, 12, 10))
        self.assertEqual(predicted.transaction.source_type, "pluggy_projection")
        real = deepcopy(self.raw)
        real["id"] = str(uuid4())
        real["creditCardMetadata"].update(installmentNumber=3, billId=str(uuid4()))
        next_bill = {**self.bill, "id": real["creditCardMetadata"]["billId"], "dueDate": "2026-12-10"}
        self.ingest(rows=[self.raw, real], bills=[self.bill, next_bill])
        next_row = ExternalTransaction.objects.get(external_id=real["id"])
        confirm(self.user, next_row.pk, 1, "link", {"transaction_id": predicted.transaction_id})
        predicted.refresh_from_db()
        self.assertTrue(predicted.confirmed)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_pending_open_bill_is_reviewable_with_explicit_due_date_estimate(self):
        self.raw["status"] = "PENDING"
        self.raw["creditCardMetadata"]["billId"] = None
        row = self.mapped()
        with self.assertRaises(ValidationError):
            confirm(self.user, row.pk, 1, "create", self.create_data())
        confirmed = confirm(
            self.user, row.pk, 1, "create", self.create_data(payment_date="2026-12-10", confirm_estimate=True)
        )
        self.assertFalse(confirmed.transaction.effected)

    def test_credit_payment_is_not_imported_as_new_expense(self):
        self.raw["type"], self.raw["amount"] = "CREDIT", -100
        row = self.mapped()
        with self.assertRaises(ValidationError):
            confirm(self.user, row.pk, 1, "create", self.create_data())
        self.assertFalse(Transaction.objects.exists())

    def test_subcategory_must_belong_to_selected_category(self):
        row = self.mapped()
        other = Category.objects.create(type="saida", description="Other")
        with self.assertRaises(ObjectDoesNotExist):
            confirm(self.user, row.pk, 1, "create", self.create_data(category_id=other.pk))
        self.assertFalse(Transaction.objects.exists())

    def test_missing_category_is_reported_as_actionable_validation(self):
        row = self.mapped()
        for key, message in (("category_id", "Selecione a categoria"), ("subcategory_id", "Selecione a subcategoria")):
            with self.assertRaisesMessage(ValidationError, message):
                confirm(self.user, row.pk, 1, "create", self.create_data(**{key: ""}))
        self.assertFalse(Transaction.objects.exists())

    def test_link_to_already_reconciled_entry_identifies_previous_source(self):
        row = self.mapped()
        local = self.local()
        other = ExternalTransaction.objects.create(account=row.account, external_id=uuid4(), facts=row.facts,
                                                  state="linked", transaction=local)
        with self.assertRaisesMessage(ValidationError, f"ocorrência Pluggy #{other.pk}"):
            confirm(self.user, row.pk, 1, "link", {"transaction_id": local.pk})
        row.refresh_from_db()
        self.assertIsNone(row.transaction_id)

    def test_state_does_not_expose_another_users_source(self):
        self.mapped()
        request = self.factory.get("/state/")
        request.user = self.other
        payload = json.loads(views.state(request).content)
        self.assertFalse(payload["configured"])
        self.assertEqual(payload["rows"], [])
        self.assertEqual(payload["card_numbers"], [])

    def test_bad_boolean_cannot_bypass_duplicate_review(self):
        row = self.mapped()
        request = self.factory.post(
            "/review/",
            json.dumps({"id": row.pk, "revision": 1, "action": "create", "distinct_purchase": "false"}),
            content_type="application/json",
        )
        request.user = self.user
        self.assertEqual(views.review(request).status_code, 400)

    def test_normalization_keeps_only_final_and_original_civil_dates(self):
        raw = deepcopy(self.raw)
        raw["creditCardMetadata"]["cardNumber"] = "1234567890121234"
        facts = normalize(raw)
        self.assertEqual(facts["last_four"], "1234")
        self.assertEqual(facts["date"], "2026-10-20")
        self.assertNotIn("1234567890121234", json.dumps(facts))

    def test_matching_uses_original_name_and_preserves_user_edits(self):
        from bank_sync.reconciliation import matching_candidates

        row = self.mapped()
        local = self.local(
            original_description=self.raw["description"], paid=2, installments_number=3, home_screen=False
        )
        matches = matching_candidates(row)
        self.assertTrue(matches[0]["name_matches"])
        confirm(self.user, row.pk, row.revision, "link", {"transaction_id": matches[0]["local"].pk})
        row.refresh_from_db()
        local.refresh_from_db()
        self.assertEqual(row.state, "linked")
        self.assertEqual(row.transaction_id, local.pk)
        self.assertEqual(local.description, "Manual test")
        self.assertFalse(local.home_screen)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_matching_does_not_hide_ambiguous_purchases(self):
        from bank_sync.reconciliation import matching_candidates

        row = self.mapped()
        self.local(original_description=self.raw["description"], paid=2, installments_number=3)
        other = deepcopy(self.raw)
        other["id"] = str(uuid4())
        self.ingest(rows=[self.raw, other])
        for source in ExternalTransaction.objects.all():
            self.assertTrue(matching_candidates(source))
        self.assertEqual(ExternalTransaction.objects.filter(state="new").count(), 2)

    def test_date_value_without_original_name_remains_a_suggestion(self):
        from bank_sync.reconciliation import matching_candidates

        row = self.mapped()
        local = self.local(paid=2, installments_number=3)
        matches = matching_candidates(row)
        self.assertEqual(matches[0]["local"].pk, local.pk)
        self.assertFalse(matches[0]["strong"])
        row.refresh_from_db()
        self.assertEqual(row.state, "new")

    def test_two_local_matches_are_not_automatically_linked(self):
        from bank_sync.reconciliation import matching_candidates

        row = self.mapped()
        for _ in range(2):
            self.local(original_description=self.raw["description"], paid=2, installments_number=3)
        self.assertEqual(len(matching_candidates(row)), 2)
        row.refresh_from_db()
        self.assertEqual(row.state, "new")

    def test_date_and_value_candidate_can_be_reconciled_despite_different_names_and_parcel_metadata(self):
        from bank_sync.reconciliation import matching_candidates

        row = self.mapped()
        local = self.local(home_screen=False)
        matches = matching_candidates(row)
        self.assertEqual(matches[0]["local"].pk, local.pk)
        self.assertTrue(matches[0]["date_matches"])
        self.assertFalse(matches[0]["name_matches"])
        confirmed = confirm(self.user, row.pk, row.revision, "link", {"transaction_id": local.pk})
        self.assertEqual(confirmed.state, "linked")
        local.refresh_from_db()
        self.assertEqual(local.description, "Manual test")
        self.assertEqual(local.value, 100)
        self.assertFalse(local.home_screen)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_prepare_suggests_exact_matches_without_linking_them(self):
        row = self.mapped()
        local = self.local(original_description=self.raw["description"], paid=2, installments_number=3)
        request = self.factory.post("/prepare/", json.dumps({"page": 1}), content_type="application/json")
        request.user = self.user
        with patch("bank_sync.views.classify", return_value=""), patch(
            "bank_sync.views.reverse", return_value="/card/edit/"
        ):
            response = views.prepare(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["rows"][0]["matches"][0]["id"], local.pk)
        row.refresh_from_db()
        self.assertEqual(row.state, "new")
        self.assertIsNone(row.transaction_id)

    def test_matching_excludes_already_linked_entries(self):
        from bank_sync.reconciliation import matching_candidates

        row = self.mapped()
        local = self.local()
        confirm(self.user, row.pk, row.revision, "link", {"transaction_id": local.pk})
        another = deepcopy(self.raw)
        another["id"] = str(uuid4())
        self.ingest(rows=[self.raw, another])
        other_row = ExternalTransaction.objects.get(external_id=another["id"])
        self.assertEqual(matching_candidates(other_row), [])

    def test_matching_does_not_suggest_same_value_with_unrelated_dates(self):
        from bank_sync.reconciliation import matching_candidates

        row = self.mapped()
        local = self.local()
        local.posted_date, local.payment_date = date(2025, 1, 1), date(2025, 2, 10)
        local.save()
        self.assertEqual(matching_candidates(row), [])

    def test_classifier_suggestions_are_cached_separately_and_corrections_record_feedback(self):
        from bank_sync.reconciliation import classify
        from statement.models import CategorizationFeedback

        row = self.mapped()
        original = deepcopy(row.facts)
        with patch(
            "bank_sync.reconciliation.AppConfig.get_solo",
            return_value=SimpleNamespace(enable_transaction_classifier=True),
        ), patch("bank_sync.reconciliation.TransactionClassifierClient") as client:
            client.return_value.predict.return_value = {
                "category_id": self.category.pk,
                "subcategory_id": self.subcategory.pk,
                "description": "TC description",
            }
            self.assertEqual(classify(self.user, [row]), "")
            self.assertEqual(classify(self.user, [row]), "")
            self.assertEqual(client.return_value.predict.call_count, 1)
            self.assertEqual(client.return_value.predict.call_args.kwargs["source_type"], "legacy")
            self.assertEqual(client.return_value.predict.call_args.kwargs["source_app"], "Inter/MeuPluggy")
        row.refresh_from_db()
        self.assertEqual(row.facts, original)
        self.assertEqual(row.suggestion["description"], "TC description")
        confirm(self.user, row.pk, 1, "create", self.create_data(description="My correction"))
        confirm(self.user, row.pk, 1, "create", self.create_data(description="My correction"))
        self.assertEqual(CategorizationFeedback.objects.count(), 1)
        self.assertEqual(CategorizationFeedback.objects.get().original_description, original["description"])

    def test_raw_bill_groups_include_imported_rows_and_separate_bill_payments(self):
        from bank_sync.presentation import ledger_data, select_bill

        row = self.mapped()
        confirm(self.user, row.pk, 1, "create", self.create_data(description="User renamed merchant"))
        payment = deepcopy(self.raw)
        payment["id"], payment["description"], payment["type"], payment["amount"] = (
            str(uuid4()),
            "PAGAMENTO ON LINE",
            "CREDIT",
            -50,
        )
        payment["creditCardMetadata"]["cardNumber"] = "5678"
        self.ingest(rows=[self.raw, payment])
        ledger = ledger_data(self.user)
        self.assertEqual(ledger["count"], 2)
        self.assertEqual(len(ledger["groups"]), 2)
        self.assertEqual(ledger["totals"]["BRL"]["net"], Decimal("100.00"))
        self.assertEqual(ledger["totals"]["BRL"]["payments"], Decimal("50.00"))
        imported = next(group for group in ledger["groups"] if group["last_four"] == "1234")["rows"][0]
        self.assertEqual(imported["facts"]["description"], self.raw["description"])
        self.assertEqual(imported["state"], "imported")
        self.assertEqual(imported["due_date"], date(2026, 11, 10))
        self.assertEqual(ledger_data(self.other)["count"], 0)
        with self.assertRaises(ObjectDoesNotExist):
            select_bill(self.other, ledger["selected_bill"])

    def test_import_review_filters_by_bill_and_excludes_linked_and_conflicting_rows(self):
        row = self.mapped()
        bill = ExternalBill.objects.get(external_id=self.bill_id)
        other_raw = deepcopy(self.raw)
        other_raw["id"] = str(uuid4())
        other_raw["creditCardMetadata"]["billId"] = str(uuid4())
        old_bill = {**self.bill, "id": other_raw["creditCardMetadata"]["billId"], "dueDate": "2026-10-10"}
        self.ingest(rows=[self.raw, other_raw], bills=[self.bill, old_bill])
        with patch("bank_sync.views.reverse", return_value="/card/edit/"):
            data = views.state_data(self.user, {})
            self.assertEqual(data["selected_bill"], str(bill.pk))
            self.assertEqual(data["count"], 1)
            confirm(self.user, row.pk, 1, "create", self.create_data())
            self.assertEqual(views.state_data(self.user, {})["count"], 0)
            self.assertEqual(views.state_data(self.user, {"bill": "all"})["count"], 1)
