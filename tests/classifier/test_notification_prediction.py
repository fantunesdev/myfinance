from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import modelform_factory

from login.models import User
from statement.models import CategorizationFeedback, Category, Currency, Notification, Subcategory, Transaction
from statement.services.core.categorization_feedback import CategorizationFeedbackService
from statement.services.core.file_handler import FileHandlerService
from statement.services.core.notification import NotificationService
from statement.services.core.transaction import TransactionService
from statement.utils.transaction_input import identify_event, parse_amount, parse_notification


def notification(message, title="Compra no crédito", app="br.com.intermedium"):
    return SimpleNamespace(
        message=message, title=title, app=app, pk=1, created_at=datetime(2026, 11, 1, 1, 30, tzinfo=timezone.utc)
    )


@pytest.mark.parametrize("merchant", ["JACOMAR", "RAIA3419", "MP*JEANASSADOS", "LOJA 99", "MERCEARIA.COM"])
@pytest.mark.parametrize("suffix", ["", ". A compra foi aprovada."])
def test_merchant_extraction_handles_branch_digits_symbols_and_end_of_message(merchant, suffix):
    data = parse_notification(notification(f"Você acaba de comprar R$ 69,71 em {merchant}{suffix}"))
    assert data["merchant_description"] == merchant
    assert data["value"] == 69.71
    assert data["event_type"] == "purchase"
    assert not data["needs_review"]


def test_notification_facts_keep_raw_message_and_local_date():
    item = notification("Você acaba de comprar R$ 69,71 em JACOMAR")
    data = NotificationService.build_transaction_from_notification(item, user=None)
    assert data["original_description"] == item.message
    assert data["source_type"] == "notification"
    assert data["source_app"] == item.app
    assert str(data["posted_date"]) == "2026-10-31"


@pytest.mark.parametrize(
    "description,amount,expected",
    [
        ("PAGAMENTO ON LINE", -4998.32, "card_payment"),
        ("Pagamento da fatura recebido", 500, "card_payment"),
        ("Estorno RAIA3419", -50, "refund"),
        ("Extorno RAIA3419", 50, "refund"),
        ("Compra negada", 10, "unknown"),
        ("Ajuste sem identificação", -10, "unknown"),
    ],
)
def test_event_detection_uses_description_and_not_only_negative_sign(description, amount, expected):
    assert identify_event(description, amount=Decimal(str(amount))) == expected


def test_unrecognized_template_requests_review_without_inventing_zero_amount():
    data = parse_notification(notification("Seu cartão está disponível", title="Aviso"))
    assert data["value"] is None
    assert data["merchant_description"] == ""
    assert data["event_type"] == "unknown"
    assert data["needs_review"]


@pytest.mark.parametrize(
    "value,expected",
    [("R$ 1.234,56", "1234.56"), ("-R$ 69,71", "-69.71"), ("R$ -69,71", "-69.71"), ("R$ 35.90", "35.90")],
)
def test_signed_amount_is_preserved(value, expected):
    assert parse_amount(value) == Decimal(expected)


def test_csv_payment_and_refund_stay_visible_for_user_review():
    content = 'Data,Lançamento,Categoria,Valor\n27/10/2026,PAGAMENTO ON LINE,OUTROS,"-R$ 500,00"\n27/10/2026,ESTORNO RAIA,DROGARIA,"-R$ 50,00"\n'
    request = SimpleNamespace(
        FILES={"file": SimpleUploadedFile("fatura.csv", content.encode())},
        user=SimpleNamespace(id=1),
        data={
            "csv_mode": "configurable",
            "date_column": "Data",
            "description_column": "Lançamento",
            "value_column": "Valor",
            "account": "",
            "card": "",
        },
    )
    with patch("statement.services.core.file_handler.AppConfig") as config, patch(
        "statement.services.core.file_handler.TransactionClassifierClient"
    ) as factory, patch.object(FileHandlerService, "_find_duplicate_transaction", return_value=None):
        config.get_solo.return_value.enable_transaction_classifier = True
        factory.return_value.predict.return_value = {
            "category_id": None,
            "subcategory_id": None,
            "description": "ESTORNO RAIA",
        }
        rows = FileHandlerService(request).read_file()
    assert len(rows) == 2
    assert rows[0]["event_type"] == "card_payment"
    assert rows[1]["event_type"] == "refund"
    assert all(row["needs_review"] for row in rows)
    assert Decimal(str(rows[0]["value"])) == Decimal("-500")
    assert factory.return_value.predict.call_count == 1


@pytest.mark.django_db
def test_confirmed_transaction_and_feedback_keep_source_and_reject_other_users_notifications():
    from datetime import date

    user = User.objects.create(username="notification-train", email="nt@test.invalid")
    other = User.objects.create(username="other-notification", email="ot@test.invalid")
    source = Notification.objects.create(user=user, app="bank", title="Compra", message="Mensagem original " * 40)
    category = Category.objects.create(description="Alimentação", type="saida")
    subcategory = Subcategory.objects.create(description="Mercado", category=category)
    Currency.objects.get_or_create(id="BRL", defaults={"description": "Real", "symbol": "R$"})
    data = dict(
        description="Supermercado",
        merchant_description="JACOMAR",
        source_notification=source.pk,
        event_type="purchase",
        category=category.pk,
        subcategory=subcategory.pk,
        currency="BRL",
        value=10,
        type="saida",
        installments_number=0,
        paid=0,
        posted_date=date(2026, 11, 1),
        payment_date=date(2026, 11, 1),
    )
    form_type = modelform_factory(Transaction, exclude=["user"])
    form = form_type(data)
    assert form.is_valid(), form.errors
    item = TransactionService.create(form, user)
    assert item.source_notification == source
    assert item.source_app == "bank"
    assert item.original_description == source.message
    assert item.merchant_description == "JACOMAR"
    assert len(item.original_description) > 255

    data["source_notification"] = Notification.objects.create(
        user=other, app="bank", title="Compra", message="Outra compra"
    ).pk
    form = form_type(data)
    assert form.is_valid(), form.errors
    with pytest.raises(ValidationError):
        TransactionService.create(form, user)

    feedback_type = modelform_factory(CategorizationFeedback, exclude=["user"])
    feedback = feedback_type(
        {
            "description": "JACOMAR",
            "corrected_description": "Supermercado",
            "source_notification": source.pk,
            "merchant_description": "JACOMAR",
        }
    )
    assert feedback.is_valid(), feedback.errors
    saved = CategorizationFeedbackService.create(feedback, user)
    assert saved.original_description == source.message
    assert saved.source_notification == source


def test_purchase_amount_is_distinguished_from_remaining_credit_limit():
    data = parse_notification(
        notification("Seu limite disponível é R$ 1.000,00. Compra aprovada de R$ 35,90 em RAIA3419.")
    )
    assert data["value"] == 35.90
    assert data["merchant_description"] == "RAIA3419"


@pytest.mark.django_db
def test_unpredicted_categories_can_be_corrected_and_mismatched_hierarchy_is_rejected():
    user = User.objects.create(username="novel-merchant", email="novel@test.invalid")
    category = Category.objects.create(description="Alimentação", type="saida")
    other = Category.objects.create(description="Casa", type="saida")
    subcategory = Subcategory.objects.create(description="Mercado", category=category)
    form_type = modelform_factory(CategorizationFeedback, exclude=["user"])
    data = {
        "description": "NOVO MERCADO",
        "corrected_description": "Mercado",
        "corrected_subcategory_id": subcategory.pk,
    }
    form = form_type(data)
    assert form.is_valid(), form.errors
    item = CategorizationFeedbackService.create(form, user)
    assert item.predicted_subcategory_id is None
    assert item.corrected_category_id_id == category.pk
    form = form_type({**data, "corrected_category_id": other.pk})
    assert form.is_valid(), form.errors
    with pytest.raises(ValidationError):
        CategorizationFeedbackService.create(form, user)


def test_refunds_keep_the_merchant_separate_from_the_event_marker():
    from statement.utils.transaction_input import statement_merchant

    assert identify_event("Compra estornada em RAIA3419", amount=Decimal("10")) == "refund"
    assert statement_merchant("ESTORNO RAIA3419", "refund") == "RAIA3419"
