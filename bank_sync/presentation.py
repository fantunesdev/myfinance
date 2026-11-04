from collections import defaultdict
from decimal import Decimal

from .models import ExternalBill, ExternalTransaction
from .reconciliation import event_kind
from .services import money


def select_bill(user, value=None):
    bills = ExternalBill.objects.filter(account__connection__user=user).select_related("account")
    if value == "all" or value == "unbilled":
        return value
    if value:
        return str(bills.get(pk=int(value)).pk)
    latest = bills.order_by("-due_date", "-id").first()
    return str(latest.pk) if latest else "unbilled"


def source_rows(user, bill):
    rows = ExternalTransaction.objects.filter(account__connection__user=user).select_related(
        "account__connection", "account__card", "transaction"
    )
    if bill == "unbilled":
        return rows.filter(facts__bill_id="")
    if bill == "all":
        return rows
    selected = ExternalBill.objects.get(pk=int(bill), account__connection__user=user)
    return rows.filter(account_id=selected.account_id, facts__bill_id=str(selected.external_id))


def bill_options(user):
    return [
        {
            "id": str(b.pk),
            "account": b.account.name,
            "due_date": b.due_date,
            "closing_date": b.closing_date,
            "total": b.total,
            "currency": b.currency,
        }
        for b in ExternalBill.objects.filter(account__connection__user=user)
        .select_related("account")
        .order_by("-due_date", "-id")
    ]


def ledger_data(user, value=None):
    selected = select_bill(user, value)
    due_dates = {
        (bill.account_id, str(bill.external_id)): bill.due_date
        for bill in ExternalBill.objects.filter(account__connection__user=user)
    }
    groups = {}
    for row in source_rows(user, selected).order_by("facts__last_four", "facts__date", "id"):
        facts = row.facts
        key = (row.account_id, facts["last_four"], facts["currency"])
        if key not in groups:
            groups[key] = {
                "account": row.account.name,
                "last_four": facts["last_four"],
                "currency": facts["currency"],
                "charges": Decimal(0),
                "refunds": Decimal(0),
                "payments": Decimal(0),
                "rows": [],
            }
        group = groups[key]
        kind = event_kind(facts)
        field = "payments" if kind == "card_payment" else "refunds" if kind == "refund" else "charges"
        group[field] += abs(money(facts["amount"]))
        group["rows"].append(
            {
                "id": row.pk,
                "facts": facts,
                "state": row.state,
                "revision": row.revision,
                "transaction_id": row.transaction_id,
                "event": kind,
                "due_date": due_dates.get((row.account_id, facts["bill_id"])),
            }
        )
    totals = defaultdict(lambda: {"charges": Decimal(0), "refunds": Decimal(0), "payments": Decimal(0)})
    for group in groups.values():
        group["net"] = group["charges"] - group["refunds"]
        for field in ("charges", "refunds", "payments"):
            totals[group["currency"]][field] += group[field]
    for total in totals.values():
        total["net"] = total["charges"] - total["refunds"]
    return {
        "selected_bill": selected,
        "bills": bill_options(user),
        "groups": list(groups.values()),
        "totals": dict(totals),
        "count": sum(len(group["rows"]) for group in groups.values()),
    }
