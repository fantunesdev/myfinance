import json
from math import ceil

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from clients.pluggy.reader import ProbeError
from statement.models import Card, CardNumber, Category, Subcategory

from .models import BankConnection, ExternalAccount, ExternalTransaction
from .presentation import bill_options, ledger_data, select_bill, source_rows
from .reconciliation import classify, event_kind, matching_candidates
from .services import (
    candidates,
    confirm,
    due_date,
    map_account,
    mapping,
    payment_due_date,
    sync_connection,
)


def api_errors(view):
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return JsonResponse({"detail": "Registro não encontrado ou sem permissão."}, status=404)
        except (ValidationError, ProbeError) as error:
            return JsonResponse(
                {"detail": " ".join(error.messages) if isinstance(error, ValidationError) else str(error)}, status=400
            )
        except (ValueError, TypeError, KeyError):
            return JsonResponse({"detail": "Dados inválidos. Recarregue a revisão."}, status=400)

    return wrapped


def body(request):
    data = json.loads(request.body)
    if not isinstance(data, dict):
        raise ValueError
    return data


def state_data(user, params):
    connections = BankConnection.objects.filter(user=user)
    accounts = ExternalAccount.objects.filter(connection__in=connections).select_related("card")
    account_data = []
    for account in accounts:
        account_data.append(
            {
                "id": account.pk,
                "name": account.name,
                "card_id": account.card_id,
                "edit_card_url": reverse("update_card", args=[account.card_id]) if account.card_id else None,
                "used_limit": account.used_limit,
                "currency": account.currency,
                "identifiers": list(account.identifiers.values("last_four", "card_number_id")),
                "bills": list(
                    account.bills.order_by("-due_date").values("due_date", "closing_date", "total", "currency")
                ),
            }
        )
    selected_bill = select_bill(user, params.get("bill") or "unbilled")
    rows = source_rows(user, selected_bill)
    requested = params.get("state", "new")
    if requested == "new":
        rows = rows.filter(state="new", transaction__isnull=True)
    elif requested != "all":
        rows = rows.filter(state=requested)
    if params.get("account"):
        rows = rows.filter(account_id=int(params["account"]))
    count = rows.count()
    page = min(max(1, int(params.get("page", 1))), max(1, ceil(count / 25)))
    output = []
    for row in rows.order_by("-facts__date", "-id")[(page - 1) * 25 : page * 25]:
        try:
            number = mapping(row)
            mapped = {"id": number.pk, "name": number.display_name}
        except ValidationError:
            mapped = None
        output.append(
            {
                "id": row.pk,
                "account_id": row.account_id,
                "revision": row.revision,
                "state": row.state,
                "facts": row.facts,
                "suggestion": row.suggestion,
                "event": event_kind(row.facts),
                "matches": [
                    {
                        "id": match["local"].pk,
                        "description": match["local"].description,
                        "payment_date": match["local"].payment_date,
                        "posted_date": match["local"].posted_date,
                        "number": match["local"].paid,
                        "total": match["local"].installments_number,
                        "value": match["local"].value,
                        "date_matches": match["date_matches"],
                        "due_matches": match["due_matches"],
                        "strong": match["strong"],
                        "original_description": match["local"].original_description,
                    }
                    for match in matching_candidates(row)[:3]
                ]
                if row.state == "new"
                else [],
                "card_number": mapped,
                "due_date": due_date(row),
                "payment_date": payment_due_date(row),
                "transaction_id": row.transaction_id,
            }
        )
    return {
        "configured": connections.exists(),
        "selected_bill": selected_bill,
        "bills": bill_options(user),
        "accounts": account_data,
        "rows": output,
        "count": count,
        "page": page,
        "pages": max(1, ceil(count / 25)),
        "connections": [
            {
                "id": c.pk,
                "status": c.status,
                "last_sync_at": c.last_sync_at,
                "consent_expires_at": c.consent_expires_at,
                "running": bool(c.lease_until and c.lease_until > timezone.now()),
                "prefer_pluggy": c.prefer_pluggy,
                "last_run": c.runs.order_by("-id").values("state", "message", "started_at", "finished_at").first(),
            }
            for c in connections
        ],
        "cards": list(Card.objects.filter(user=user).values("id", "description")),
        "card_numbers": [
            {"id": n.pk, "card_id": n.card_id, "name": n.display_name}
            for n in CardNumber.objects.filter(card__user=user)
        ],
        "categories": list(Category.objects.values("id", "description", "type")),
        "subcategories": list(Subcategory.objects.values("id", "description", "category_id")),
    }


@login_required
@require_GET
@api_errors
def state(request):
    return JsonResponse(state_data(request.user, request.GET))


@login_required
@require_POST
@api_errors
def prepare(request):
    params = body(request)
    selected = select_bill(request.user, params.get("bill") or "unbilled")
    pending = source_rows(request.user, selected).filter(state="new", transaction__isnull=True)
    page = min(max(1, int(params.get("page", 1))), max(1, ceil(pending.count() / 25)))
    rows = list(pending.order_by("-facts__date", "-id")[(page - 1) * 25 : page * 25])
    notice = classify(request.user, rows)
    result = state_data(request.user, {**params, "bill": selected, "page": page, "state": "new"})
    result.update(classifier_notice=notice)
    return JsonResponse(result)


@login_required
@require_GET
def bills_page(request):
    return render(request, "bank_sync/bills.html", {
        "pluggy_connections": BankConnection.objects.filter(user=request.user).only("consent_expires_at"),
    })


@login_required
@require_GET
@api_errors
def ledger(request):
    return JsonResponse(ledger_data(request.user, request.GET.get("bill")))


@login_required
@require_GET
@api_errors
def export_ledger(request, format):
    from .exports import csv_response, pdf_response, pdf_brands, selected_cards

    if format not in ("csv", "pdf"):
        raise ValidationError("Formato de exportação inválido.")
    data = ledger_data(request.user, request.GET.get("bill"))
    if format == "pdf" and "card" in request.GET:
        data = selected_cards(data, request.GET.getlist("card"))
    brands = pdf_brands(request.user, data)
    data["bank_names"] = [brand["bank_name"] for brand in brands]
    response = csv_response(data) if format == "csv" else pdf_response(data, brands)
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_POST
@api_errors
def sync(request):
    connection = BankConnection.objects.get(pk=body(request)["connection_id"], user=request.user)
    run = sync_connection(connection)
    return JsonResponse({"count": run.transaction_count})


@login_required
@require_POST
@api_errors
def map_cards(request):
    data = body(request)
    if not isinstance(data.get("aliases", {}), dict):
        raise ValueError
    ext = map_account(request.user, data["account_id"], data["card_id"], data.get("aliases", {}))
    return JsonResponse({"id": ext.pk})


@login_required
@require_POST
@api_errors
def review(request):
    data = body(request)
    for key in ("distinct_purchase", "project_remaining", "confirm_estimate"):
        if key in data and type(data[key]) is not bool:
            raise ValueError
    row = confirm(request.user, data["id"], data["revision"], data["action"], data)
    return JsonResponse(
        {
            "id": row.pk,
            "state": row.state,
            "transaction_id": row.transaction_id,
            "reconciled_count": getattr(row, "reconciled_count", 1),
            "remaining_installments": getattr(row, "remaining_installments", 0),
        }
    )


@login_required
@require_GET
@api_errors
def details(request, row_id):
    row = ExternalTransaction.objects.select_related("account__connection", "account__card").get(
        pk=row_id, account__connection__user=request.user
    )
    return JsonResponse(
        {
            "candidates": [
                {
                    "id": t.pk,
                    "description": t.description,
                    "value": t.value,
                    "payment_date": t.payment_date,
                    "paid": t.paid,
                    "total": t.installments_number,
                    "source_type": t.source_type,
                }
                for t in candidates(row)
            ]
        }
    )


@login_required
@require_POST
@api_errors
def predict(request):
    row = ExternalTransaction.objects.get(pk=body(request)["id"], account__connection__user=request.user)
    notice = classify(request.user, [row], force=True)
    return JsonResponse({"detail": notice}, status=400) if notice else JsonResponse(row.suggestion)


@login_required
@require_POST
@api_errors
def preference(request):
    data = body(request)
    if type(data.get("prefer_pluggy")) is not bool:
        raise ValueError
    connection = BankConnection.objects.get(pk=data["connection_id"], user=request.user)
    connection.prefer_pluggy = data["prefer_pluggy"]
    connection.save(update_fields=["prefer_pluggy"])
    return JsonResponse({"ok": True})


@login_required
@require_POST
@api_errors
def sync_investment_positions(request):
    from bank_sync.investments import sync_investments
    connection_id = body(request).get('connection_id')
    connections = BankConnection.objects.filter(user=request.user)
    if not connection_id and connections.count() != 1:
        raise ValidationError('Configure ou selecione uma conexão Pluggy de investimentos.')
    connection = connections.get(pk=connection_id) if connection_id else connections.get()
    return JsonResponse(sync_investments(connection))
