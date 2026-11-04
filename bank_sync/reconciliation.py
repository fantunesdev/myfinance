"""Conservative matching and cached classifier suggestions for import review."""
import re
import unicodedata

from django.core.exceptions import ValidationError

from clients.transaction_classifier.transaction_classifier import TransactionClassifierClient
from statement.models import AppConfig, CategorizationFeedback, Category, Subcategory
from .models import ExternalTransaction
from .services import candidates, due_date, mapping, money, source_date

# The running TC's schema accepts csv/notification/manual/legacy. Keep the real
# provider on the financial row and source_app; use its generic external-data
# context for predictions/feedback until that service adds a Pluggy source type.
TC_SOURCE_TYPE = "legacy"


def normalized_name(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def event_kind(facts):
    if facts.get("operation") == "PAGAMENTO_FATURA":
        return "card_payment"
    if facts.get("direction") == "CREDIT":
        name = normalized_name(facts.get("description"))
        if re.search(r"\bpagamento (on line|online|recebido|de fatura|da fatura)\b", name):
            return "card_payment"
        return "refund"
    return "purchase" if facts.get("direction") == "DEBIT" else "unknown"


def matching_candidates(row):
    """A date/value suggestion is distinct from a proven unique match."""
    result = []
    facts = row.facts
    try:
        number = mapping(row)
    except ValidationError:
        number = None
    dates = {source_date(facts.get("purchase_date")), source_date(facts.get("date"))} - {None}
    name = normalized_name(facts.get("description"))
    for local in candidates(row, limit=None):
        originals = [local.original_description, local.merchant_description]
        if not any(originals):
            originals = [local.description]
        name_matches = bool(name and any(normalized_name(text) == name for text in originals if text))
        date_matches = local.posted_date in dates or local.payment_date in dates
        due = due_date(row)
        due_matches = bool(due and local.payment_date == due)
        installment_matches = facts.get("payment_type") != "INSTALLMENT" or (
            local.paid == facts.get("number") and local.installments_number == facts.get("total")
        )
        strong = bool(
            number
            and local.card_number_id == number.pk
            and date_matches
            and name_matches
            and (not due or local.payment_date == due)
            and local.type == "saida"
            and installment_matches
            and money(local.value) == abs(money(facts["amount"]))
            and not local.bank_sync_links.exists()
            and event_kind(facts) == "purchase"
        )
        result.append(
            {
                "local": local,
                "strong": strong,
                "date_matches": date_matches,
                "due_matches": due_matches,
                "name_matches": name_matches,
                "installment_matches": installment_matches,
            }
        )
    return sorted(
        result,
        key=lambda match: (
            -int(match["due_matches"]),
            -int(match["date_matches"]),
            -int(match["installment_matches"]),
            -int(match["name_matches"]),
            match["local"].pk,
        ),
    )


def classify(user, rows, force=False):
    if not AppConfig.get_solo().enable_transaction_classifier:
        return "O TC está desativado; a revisão manual continua disponível."
    client = None
    for row in rows:
        if row.state != "new" or event_kind(row.facts) != "purchase" or (row.suggestion and not force):
            continue
        try:
            client = client or TransactionClassifierClient(user)
            predicted = client.predict(
                row.facts["description"],
                source_category=row.facts["source_category"],
                source_type=TC_SOURCE_TYPE,
                source_app="Inter/MeuPluggy",
                event_type="purchase",
                merchant_description=row.facts["description"],
            )
            category = Category.objects.filter(pk=predicted.get("category_id"), type="saida").first()
            subcategory = (
                Subcategory.objects.filter(pk=predicted.get("subcategory_id"), category=category).first()
                if category
                else None
            )
            suggestion = {
                "category_id": category.pk if category else None,
                "subcategory_id": subcategory.pk if subcategory else None,
                "description": str(predicted.get("description") or row.facts["description"])[:255],
            }
            ExternalTransaction.objects.filter(pk=row.pk, revision=row.revision, state="new").update(
                suggestion=suggestion
            )
            row.suggestion = suggestion
        except Exception:
            # One failure stops this page, rather than timing out once per row.
            return "O TC não respondeu. Sugestões anteriores foram preservadas; você pode revisar manualmente."
    return ""


def save_feedback(row, target):
    predicted = row.suggestion
    if not predicted:
        return
    if (
        predicted.get("category_id") == target.category_id
        and predicted.get("subcategory_id") == target.subcategory_id
        and predicted.get("description") == target.description
    ):
        return
    CategorizationFeedback.objects.create(
        user=target.user,
        description=row.facts["description"],
        corrected_description=target.description,
        original_description=row.facts["description"],
        merchant_description=row.facts["description"],
        source_category=row.facts["source_category"],
        source_type=TC_SOURCE_TYPE,
        source_app="Inter/MeuPluggy",
        event_type="purchase",
        predicted_category_id_id=predicted.get("category_id")
        if Category.objects.filter(pk=predicted.get("category_id")).exists()
        else None,
        predicted_subcategory_id_id=predicted.get("subcategory_id")
        if Subcategory.objects.filter(pk=predicted.get("subcategory_id")).exists()
        else None,
        corrected_category_id=target.category,
        corrected_subcategory_id=target.subcategory,
    )
