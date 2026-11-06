"""Import source data first; apply financial changes only on explicit review."""
import hashlib
import json
import os
import re
import uuid
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction as db
from django.db.models import F, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from clients.pluggy.reader import PluggyReader, ProbeError
from statement.models import (
    Card,
    CardNumber,
    Category,
    Currency,
    Subcategory,
    Transaction,
)
from statement.services.core.card import CardService

from .models import (
    BankConnection,
    ExternalAccount,
    ExternalBill,
    ExternalCardIdentifier,
    ExternalTransaction,
    ProjectedInstallment,
    SyncRun,
)


def source_date(value):
    """Keep the institution's civil date; never convert date-only facts to local time."""
    return date.fromisoformat(str(value)[:10]) if value else None


def money(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or abs(result) >= Decimal("1000000000000000"):
            raise ValueError
        return result.quantize(Decimal(".01"))
    except (ValueError, InvalidOperation, TypeError):
        raise ValidationError("Valor financeiro inválido.") from None


def normalize(raw):
    meta = raw.get("creditCardMetadata") or {}
    number = re.sub(r"\D", "", str(meta.get("cardNumber") or ""))[-4:]
    facts = {
        "description": str(raw.get("descriptionRaw") or raw.get("description") or "")[:255],
        "amount": str(money(raw["amount"])),
        "currency": raw.get("currencyCode"),
        "date": str(source_date(raw.get("date")) or ""),
        "purchase_date": str(source_date(meta.get("purchaseDate")) or ""),
        "status": raw.get("status"),
        "direction": raw.get("type"),
        "operation": raw.get("operationType"),
        "last_four": number,
        "bill_id": str(meta.get("billId") or ""),
        "forecast": meta.get("billForecastDate"),
        "payment_type": meta.get("paymentType"),
        "number": meta.get("installmentNumber"),
        "total": meta.get("totalInstallments"),
        "source_category": str(raw.get("category") or "")[:255],
    }
    return facts


def plan_fingerprint(facts):
    # A suggestion key, never sufficient to automatically merge two purchases.
    if not facts.get("purchase_date") or not facts.get("last_four") or not facts.get("total"):
        return ""
    fields = [facts.get(k) for k in ("description", "purchase_date", "last_four", "total", "currency")]
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False).encode()).hexdigest()


def configured_reader():
    # Explicit file, same credential source as the probe, never sent to the browser.
    from dotenv import dotenv_values

    values = dotenv_values(settings.BASE_DIR / ".env.pluggy") if hasattr(settings, "BASE_DIR") else {}

    def get(key):
        return os.environ.get(key) or values.get(key)

    if not get("PLUGGY_CLIENT_ID") or not get("PLUGGY_CLIENT_SECRET"):
        raise ValidationError("Configure as credenciais Pluggy no servidor.")
    return PluggyReader(get("PLUGGY_CLIENT_ID"), get("PLUGGY_CLIENT_SECRET"))


def sync_connection(connection, reader=None):
    token, now = uuid.uuid4(), timezone.now()
    acquired = (
        BankConnection.objects.filter(pk=connection.pk)
        .filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now))
        .update(lease_until=now + timedelta(minutes=15), lease_token=token)
    )
    if not acquired:
        raise ValidationError("Esta conexão já está sendo consultada. Aguarde.")
    run = SyncRun.objects.create(connection=connection)
    try:
        reader = reader or configured_reader()
        reader.authenticate()
        item = reader.request("/items/" + str(connection.item_id))
        expires = parse_datetime(item.get("consentExpiresAt") or "")
        if expires and timezone.is_naive(expires):
            expires = timezone.make_aware(expires)
        if (
            (expires and expires <= timezone.now())
            or item.get("status") != "UPDATED"
            or item.get("executionStatus") not in (None, "SUCCESS")
        ):
            raise ValidationError("Conexão sem atualização completa ou autorização expirada. Confira o Meu Pluggy.")
        accounts = reader.numbered("/accounts", {"itemId": str(connection.item_id), "type": "CREDIT"})
        snapshot = []
        for account in accounts:
            if account.get("type") != "CREDIT" or account.get("subtype") != "CREDIT_CARD":
                continue
            bills = reader.numbered("/bills", {"accountId": account["id"]})
            rows = reader.transactions(account["id"])
            snapshot.append((account, bills, [(raw["id"], normalize(raw)) for raw in rows]))
        if not snapshot:
            raise ValidationError("Nenhum cartão disponível. O histórico local foi preservado.")
        with db.atomic():
            locked = BankConnection.objects.select_for_update().get(pk=connection.pk)
            if locked.lease_token != token or locked.lease_until <= timezone.now():
                raise ValidationError("Consulta excedeu o prazo; repita para obter um conjunto consistente.")
            for account, bills, rows in snapshot:
                ext, _ = ExternalAccount.objects.get_or_create(
                    external_id=account["id"],
                    defaults={
                        "connection": locked,
                        "name": account.get("name") or "Cartão",
                        "currency": account.get("currencyCode") or "",
                    },
                )
                if ext.connection_id != locked.pk:
                    raise ValidationError("Conta externa já vinculada a outra conexão.")
                ext.name = account.get("name") or "Cartão"
                ext.currency = account.get("currencyCode") or ""
                ext.used_limit = money(account["balance"]) if account.get("balance") is not None else None
                ext.save()
                for bill in bills:
                    obj, created = ExternalBill.objects.get_or_create(
                        external_id=bill["id"],
                        defaults={
                            "account": ext,
                            "total": money(bill["totalAmount"]),
                            "currency": bill.get("totalAmountCurrencyCode") or "",
                        },
                    )
                    if obj.account_id != ext.pk:
                        raise ValidationError("Fatura retornada para conta incompatível.")
                    due = source_date(bill.get("dueDate"))
                    # A due-date correction requires reviewing already confirmed entries.
                    if not created and obj.due_date != due:
                        for row in ext.transactions.select_for_update().filter(
                            transaction__isnull=False, facts__bill_id=str(bill["id"])
                        ):
                            row.state, row.revision = "conflict", row.revision + 1
                            row.save(update_fields=["state", "revision"])
                    obj.due_date, obj.closing_date = due, source_date(bill.get("billClosingDate"))
                    obj.total, obj.currency = money(bill["totalAmount"]), bill.get("totalAmountCurrencyCode") or ""
                    obj.save()
                for external_id, facts in rows:
                    row, created = ExternalTransaction.objects.select_for_update().get_or_create(
                        external_id=external_id,
                        defaults={"account": ext, "facts": facts, "fingerprint": plan_fingerprint(facts)},
                    )
                    if row.account_id != ext.pk:
                        raise ValidationError("Transação retornada para conta incompatível.")
                    if not created and row.facts != facts:
                        row.facts, row.fingerprint, row.revision = facts, plan_fingerprint(facts), row.revision + 1
                        row.suggestion = {}
                        if row.transaction_id:
                            row.state = "conflict"
                        row.save()
                    if facts["last_four"]:
                        ExternalCardIdentifier.objects.get_or_create(account=ext, last_four=facts["last_four"])
            locked.status, locked.consent_expires_at, locked.last_sync_at = (
                item.get("status", ""),
                expires,
                timezone.now(),
            )
            locked.save(update_fields=["status", "consent_expires_at", "last_sync_at"])
            run.state, run.transaction_count = "succeeded", sum(len(rows) for _, _, rows in snapshot)
            run.finished_at = timezone.now()
            run.save()
        return run
    except Exception as error:
        run.state, run.finished_at = "failed", timezone.now()
        run.message = (
            str(error)[:255]
            if isinstance(error, (ValidationError, ProbeError))
            else "Consulta falhou; nenhum lote parcial foi confirmado."
        )
        run.save(update_fields=["state", "finished_at", "message"])
        raise
    finally:
        BankConnection.objects.filter(pk=connection.pk, lease_token=token).update(lease_until=None, lease_token=None)


@db.atomic
def map_account(user, account_id, card_id, aliases):
    ext = ExternalAccount.objects.select_for_update().get(pk=account_id, connection__user=user)
    card = Card.objects.get(pk=card_id, user=user)
    previous_card = ext.card_id
    changed_mapping = previous_card is not None and previous_card != card.pk
    if ext.card_id and ext.card_id != card.pk and ext.transactions.filter(transaction__isnull=False).exists():
        raise ValidationError("Conta já possui lançamentos confirmados; revise-os antes de trocar o cartão.")
    ext.card = card
    ext.save(update_fields=["card"])
    for alias in ext.identifiers.all():
        previous_number = alias.card_number_id
        chosen = aliases.get(alias.last_four)
        if chosen:
            alias.card_number = CardNumber.objects.get(pk=chosen, card=card, card__user=user)
        else:
            matches = [n for n in card.card_numbers.all() if n.last_four_digits == alias.last_four]
            alias.card_number = matches[0] if len(matches) == 1 else None
        if alias.card_number_id != ExternalCardIdentifier.objects.get(pk=alias.pk).card_number_id:
            if ext.transactions.filter(transaction__isnull=False, facts__last_four=alias.last_four).exists():
                raise ValidationError("Identificação já usada; confirme os lançamentos antes de remapear.")
        changed_mapping = changed_mapping or (previous_number is not None and previous_number != alias.card_number_id)
        alias.save(update_fields=["card_number"])
    if changed_mapping:
        ext.transactions.update(revision=F("revision") + 1)
    return ext


def mapping(row):
    ext = row.account
    if not ext.card_id or ext.card.user_id != ext.connection.user_id:
        raise ValidationError("Associe a conta externa a um cartão seu.")
    alias = ext.identifiers.filter(last_four=row.facts["last_four"]).select_related("card_number").first()
    if not alias or not alias.card_number_id or alias.card_number.card_id != ext.card_id:
        raise ValidationError("Identifique o número do cartão antes de confirmar.")
    return alias.card_number


def due_date(row):
    bill = row.account.bills.filter(external_id=row.facts["bill_id"]).first() if row.facts["bill_id"] else None
    return bill.due_date if bill else None


def payment_due_date(row, estimate=None):
    """Prefer the bank's bill; otherwise reuse the transaction form's card rule."""
    official = due_date(row)
    if official:
        return official
    if estimate:
        return source_date(estimate)
    card = row.account.card
    # facts.date describes this installment, whereas purchase_date is the
    # original purchase and would move later installments back to the first bill.
    posted = source_date(row.facts.get("date") or row.facts.get("purchase_date"))
    if not card or not posted:
        return None
    try:
        return CardService.set_processing_date(card, posted)
    except ValueError:
        raise ValidationError("Confira os dias de fechamento e vencimento do cartão cadastrado.") from None


def candidates(row, limit=20):
    """Suggestions only; fuzzy matching never discards a financial occurrence."""
    ext, facts = row.account, row.facts
    if not ext.card_id:
        return Transaction.objects.none()
    dates = {source_date(facts.get("purchase_date")), source_date(facts.get("date"))} - {None}
    due = due_date(row)
    if not dates and not due:
        return Transaction.objects.none()
    date_filter = Q(posted_date__in=dates) | Q(payment_date__in=dates)
    if due:
        date_filter |= Q(payment_date=due)
    amount = abs(money(facts["amount"]))
    qs = Transaction.objects.filter(
        date_filter,
        user=ext.connection.user,
        card_id=ext.card_id,
        currency_id=facts["currency"],
        type="saida" if facts.get("direction") == "DEBIT" else "entrada",
        value__range=(float(amount - Decimal("0.005")), float(amount + Decimal("0.005"))),
        bank_sync_links__isnull=True,
    )
    try:
        number = mapping(row)
        qs = qs.filter(Q(card_number=number) | Q(card_number__isnull=True))
    except ValidationError:
        pass
    qs = qs.order_by("payment_date", "id")
    return qs if limit is None else qs[:limit]


def choose_category(category_id, subcategory_id, direction):
    if not str(category_id or "").isdigit():
        raise ValidationError("Selecione a categoria da compra antes de cadastrar.")
    if not str(subcategory_id or "").isdigit():
        raise ValidationError("Selecione a subcategoria da compra antes de cadastrar.")
    category = Category.objects.get(pk=category_id, type=direction)
    subcategory = Subcategory.objects.get(pk=subcategory_id, category=category)
    return category, subcategory


def reconcile_installments(user, row, target):
    """Extend an explicit match only to unambiguous occurrences of that purchase."""
    facts = row.facts
    if facts.get("payment_type") != "INSTALLMENT" or not row.fingerprint:
        return 1, 0
    siblings = list(
        ExternalTransaction.objects.select_for_update()
        .filter(account=row.account, fingerprint=row.fingerprint)
        .order_by("pk")
    )
    # Two purchases with the same merchant/date/card can share a fingerprint.
    sequences = [item.facts.get("number") for item in siblings]
    pending = [item for item in siblings if item.pk != row.pk and item.state == "new" and not item.transaction_id]
    count, remaining = 1, 0
    for sibling in pending:
        source = sibling.facts
        sequence = source.get("number")
        due = due_date(sibling)
        if (
            not sequence
            or sequences.count(sequence) != 1
            or sequences.count(facts.get("number")) != 1
            or source.get("payment_type") != "INSTALLMENT"
            or source.get("direction") != facts.get("direction")
            or source.get("operation") != facts.get("operation")
            or abs(money(source["amount"]) - money(facts["amount"])) > Decimal("0.01")
            or source.get("status") not in ("POSTED", "PENDING")
            or not due
            or target.paid != facts.get("number")
            or target.installments_number != facts.get("total")
        ):
            remaining += 1
            continue
        matches = candidates(sibling, limit=None).filter(
            paid=sequence,
            installments_number=source.get("total"),
            payment_date=due,
        )
        if target.installment_id:
            matches = matches.filter(installment_id=target.installment_id)
        else:
            dates = {target.posted_date}
            if target.posted_date:
                dates.add(target.posted_date + relativedelta(months=sequence - facts["number"]))
            matches = matches.filter(card_number=target.card_number, posted_date__in=dates).filter(
                Q(description=target.description)
                | Q(original_description=facts.get("description"))
                | Q(merchant_description=facts.get("description"))
            )
        matches = list(matches[:2])
        if len(matches) != 1:
            remaining += 1
            continue
        confirm(user, sibling.pk, sibling.revision, "link", {"transaction_id": matches[0].pk}, reconcile_group=False)
        count += 1
    return count, remaining


@db.atomic
def confirm(user, row_id, revision, action, data, *, reconcile_group=True):
    # Shared owner lock follows the financial domain's locking order.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    row = (
        ExternalTransaction.objects.select_for_update()
        .select_related("account__connection", "account__card")
        .get(pk=row_id, account__connection__user=user)
    )
    if row.revision != int(revision):
        raise ValidationError("A fonte mudou. Recarregue e revise novamente.")
    if action == "unlink" and row.transaction_id:
        projection = ProjectedInstallment.objects.filter(transaction_id=row.transaction_id).first()
        if projection:
            projection.confirmed = False
            projection.save(update_fields=["confirmed"])
            target = projection.transaction
            target.source_type = "pluggy_projection"
            target.save(update_fields=["source_type"])
        row.transaction, row.state, row.revision = None, "new", row.revision + 1
        row.save(update_fields=["transaction", "state", "revision"])
        return row
    if row.state in ("imported", "linked", "ignored"):
        if action == "link" and reconcile_group and row.transaction_id == int(data["transaction_id"]):
            row.reconciled_count, row.remaining_installments = reconcile_installments(user, row, row.transaction)
        return row
    if action == "keep" and row.transaction_id and row.state == "conflict":
        row.state = "linked"
        row.save(update_fields=["state"])
        return row
    if action == "ignore" and not row.transaction_id:
        row.state = "ignored"
        row.save(update_fields=["state"])
        return row
    if row.transaction_id:
        raise ValidationError("Há lançamento vinculado. Revise-o e escolha manter o lançamento local.")
    number = mapping(row)
    facts = row.facts
    if facts["currency"] != "BRL" or facts["status"] not in ("POSTED", "PENDING"):
        raise ValidationError("Moeda ou estado ainda não suportado para confirmação.")
    if action == "link":
        if not str(data.get("transaction_id") or "").isdigit():
            raise ValidationError("Informe o ID do lançamento existente antes de vincular.")
        target = Transaction.objects.select_for_update().get(
            pk=data["transaction_id"], user=user, card_id=row.account.card_id
        )
        if target.card_number_id not in (None, number.pk):
            raise ValidationError("O lançamento pertence a outro número de cartão.")
        previous = target.bank_sync_links.exclude(pk=row.pk).first()
        if previous:
            raise ValidationError(
                f"O lançamento #{target.pk} já está conciliado com a ocorrência Pluggy #{previous.pk}. "
                "Confira o vínculo em Faturas originais; para substituí-lo, desfaça primeiro o vínculo anterior."
            )
        projection = ProjectedInstallment.objects.filter(transaction=target).first()
        if projection:
            if projection.fingerprint != row.fingerprint or projection.number != facts["number"]:
                raise ValidationError("Previsão incompatível com esta parcela.")
            source_due = payment_due_date(row, data.get("payment_date"))
            if money(target.value) != abs(money(facts["amount"])) or target.payment_date != source_due:
                raise ValidationError("Valor ou vencimento mudou. Ajuste a previsão antes de vincular.")
            projection.confirmed = True
            projection.save(update_fields=["confirmed"])
            target.source_type = "pluggy"
        changed = ["source_type"] if projection else []
        if target.card_number_id is None:
            target.card_number = number
            changed.append("card_number")
        if changed:
            target.save(update_fields=changed)
        row.transaction, row.state = target, "linked"
    elif action == "create":
        if (
            facts["direction"] != "DEBIT"
            or money(facts["amount"]) <= 0
            or facts["operation"] not in ("PAGAMENTO", "TARIFA")
        ):
            raise ValidationError("Pagamento, estorno ou evento especial: vincule a um lançamento revisado ou ignore.")
        if facts["payment_type"] not in ("SINGLE", "INSTALLMENT"):
            raise ValidationError("Tipo de compra não identificado; revise manualmente antes de vincular.")
        due = payment_due_date(row, data.get("payment_date"))
        if not due:
            raise ValidationError("Associe um cartão com fechamento e vencimento para calcular a data de pagamento.")
        category, subcategory = choose_category(data["category_id"], data["subcategory_id"], "saida")
        if candidates(row) and not data.get("distinct_purchase"):
            raise ValidationError("Há lançamentos parecidos. Vincule um deles ou confirme que esta compra é distinta.")
        current, total = facts["number"], facts["total"]
        if facts["payment_type"] == "INSTALLMENT" and (
            type(current) is not int or type(total) is not int or not 1 <= current <= total <= 120
        ):
            raise ValidationError("Dados de parcelamento incompletos ou inválidos.")
        if facts["payment_type"] == "SINGLE":
            current, total = 0, 0
        target = Transaction(
            user=user,
            card=row.account.card,
            card_number=number,
            category=category,
            subcategory=subcategory,
            type="saida",
            value=float(money(data.get("value", abs(money(facts["amount"]))))),
            currency=Currency.objects.get(pk="BRL"),
            posted_date=source_date(data.get("posted_date") or facts["purchase_date"] or facts["date"]),
            payment_date=due,
            description=(data.get("description") or facts["description"])[:255],
            original_description=facts["description"],
            source_category=facts["source_category"],
            source_type="pluggy",
            source_app="Inter/MeuPluggy",
            event_type="purchase",
            installments_number=total,
            paid=current,
            effected=False,
            home_screen=number.home_screen,
        )
        # Legacy plan editing renumbers from 1. Bank installments are individual
        # occurrences and may first arrive at an intermediate installment.
        if target.value <= 0:
            raise ValidationError("O valor da compra deve ser positivo.")
        target.save()
        from .reconciliation import save_feedback

        save_feedback(row, target)
        row.transaction, row.state = target, "imported"
        if data.get("project_remaining"):
            if not total or not row.fingerprint:
                raise ValidationError("Projeção exige parcelamento com cartão e data original identificados.")
            if ProjectedInstallment.objects.filter(account=row.account, fingerprint=row.fingerprint).exists():
                raise ValidationError("Já existem previsões para compra semelhante. Concilie-as antes de projetar.")
            for sequence in range(current + 1, total + 1):
                # Do not project an installment already available from the source.
                if row.account.transactions.filter(fingerprint=row.fingerprint, facts__number=sequence).exists():
                    continue
                predicted = Transaction.objects.create(
                    user=user,
                    card=target.card,
                    card_number=number,
                    category=category,
                    subcategory=subcategory,
                    type="saida",
                    currency=target.currency,
                    value=target.value,
                    posted_date=target.posted_date,
                    payment_date=due + relativedelta(months=sequence - current),
                    description=target.description,
                    original_description=target.original_description,
                    source_type="pluggy_projection",
                    source_app="Inter/MeuPluggy",
                    event_type="purchase",
                    installments_number=total,
                    paid=sequence,
                    effected=False,
                    home_screen=number.home_screen,
                    observation="Previsão calculada pelo MyFinance; valor e vencimento sujeitos a confirmação.",
                )
                ProjectedInstallment.objects.create(
                    account=row.account, anchor=row, fingerprint=row.fingerprint, number=sequence, transaction=predicted
                )
    else:
        raise ValidationError("Ação inválida.")
    row.save(update_fields=["transaction", "state"])
    if action == "link" and reconcile_group:
        row.reconciled_count, row.remaining_installments = reconcile_installments(user, row, target)
    return row
