"""Extract statement facts without turning bank labels into personal categories."""

import re
import unicodedata
from decimal import Decimal, InvalidOperation

EVENT_CHOICES = (
    ("purchase", "Compra"),
    ("fixed_expense", "Despesa fixa"),
    ("card_payment", "Pagamento da fatura"),
    ("refund", "Estorno"),
    ("unknown", "Revisar evento"),
)


def plain_text(value):
    return unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()


def parse_amount(value):
    if value is None:
        return None
    text = str(value).replace("\xa0", "").replace(" ", "").replace("R$", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1 or ("." in text and len(text.rsplit(".", 1)[1]) == 3):
        text = text.replace(".", "")
    try:
        amount = Decimal(text)
        return amount if amount.is_finite() else None
    except InvalidOperation:
        return None


def extract_amount(message):
    money = r"(-?\s*R\$\s*-?\s*[\d.,]+)"
    # A notification can mention the remaining limit as well as the purchase.
    contextual = re.search(
        r"\b(?:compra|comprar|comprou|estorno|extorno|reembolso|pagamento)\b.{0,60}?" + money,
        message or "",
        re.IGNORECASE,
    )
    if contextual:
        return parse_amount(contextual.group(1))
    matches = re.findall(money, message or "", re.IGNORECASE)
    return parse_amount(matches[0]) if len(matches) == 1 else None


def identify_event(description, title="", amount=None, default="unknown"):
    text = plain_text(f"{title} {description}")
    if re.search(r"\b(estorno|extorno|estornad[ao]|extornad[ao]|reembolso|devolucao)\b", text):
        return "refund"
    if re.search(r"\b(compra|transacao)\b.{0,35}\b(negada|recusada|cancelada|nao autorizada)\b", text):
        return "unknown"
    if re.search(r"\bpagamento\s+(?:on\s*line|online)\b", text) or re.search(
        r"\bpagamento\b.{0,45}\bfatura\b|\bfatura\b.{0,45}\b(paga|pagamento|recebido)\b", text
    ):
        return "card_payment"
    if amount is not None and amount < 0:
        return "unknown"
    if re.search(r"\b(compra|comprar|comprou)\b", text):
        return "purchase"
    return default


def statement_merchant(description, event_type):
    if event_type == "refund":
        return re.sub(
            r"^(?:estorno|extorno|reembolso|devolu[cç][aã]o)\s*(?:(?:da )?compra\s*|de\s*|[:\-]\s*)?",
            "",
            description,
            flags=re.IGNORECASE,
        ).strip()[:255]
    return description[:255]


def extract_merchant(message, app=""):
    # The Inter template also ends directly after the merchant, without a period.
    # Keep symbols and branch digits; stop at sentence/amount/card/date boundaries.
    patterns = [
        r"\b(?:em|no estabelecimento)\s+(.+?)(?=\s+(?:no dia|dia\s+\d|com (?:o |seu )?cart[aã]o|cart[aã]o final|[aà]s\s+\d{1,2}:)|[.!?](?:\s|$)|,|\s+R\$|$)",
    ]
    if app == "br.com.intermedium":
        patterns.insert(0, r"\b(?:comprar|comprou)\s+R\$\s*[\d.,]+\s+em\s+(.+?)(?=[.!?](?:\s|$)|,|$)")
    for pattern in patterns:
        match = re.search(pattern, message or "", re.IGNORECASE)
        if match:
            merchant = match.group(1).strip().rstrip(".!?")
            if len(merchant) > 1 and not re.match(r"^(?:seu |sua |seus )?cart[aã]o\b", merchant, re.IGNORECASE):
                return merchant[:255]
    return ""


def parse_notification(notification):
    message = notification.message or ""
    title = notification.title or ""
    app = notification.app or ""
    amount = extract_amount(message)
    event_type = identify_event(message, title, amount)
    merchant = extract_merchant(message, app)
    return {
        "original_description": message,
        "merchant_description": merchant,
        "description": merchant or title[:255],
        "source_type": "notification",
        "source_app": app,
        "source_notification": getattr(notification, "pk", None),
        "event_type": event_type,
        "value": float(amount) if amount is not None else None,
        "needs_review": event_type != "purchase" or not merchant or amount is None,
        "review_reason": (
            "Pagamento da fatura: confira os dados antes de importar."
            if event_type == "card_payment"
            else (
                "Estorno: confira o valor e a classificação da compra original."
                if event_type == "refund"
                else (
                    "Confira os dados extraídos antes de cadastrar."
                    if event_type == "unknown" or not merchant or amount is None
                    else ""
                )
            )
        ),
    }
