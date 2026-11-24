"""Attach bank occurrences to the standard plan without regenerating expenses."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from bank_sync.models import ExternalTransaction, ProjectedInstallment
from statement.models import Installment, Transaction


def installment_bundle(row):
    from .services import money, payment_due_date
    facts = row.facts
    if (facts.get('payment_type') != 'INSTALLMENT' or not row.fingerprint
            or type(facts.get('total')) is not int or type(facts.get('number')) is not int
            or not 1 <= facts['number'] <= facts['total'] <= 120):
        return []
    rows = list(ExternalTransaction.objects.filter(account=row.account, fingerprint=row.fingerprint)
                .select_related('transaction', 'account__card').order_by('pk'))
    sequences, cycles = set(), set()
    tolerance = Decimal('.01') * max(1, facts['total'] - 1)
    for source in rows:
        other = source.facts
        seq = other.get('number')
        if (type(seq) is not int or seq in sequences or not 1 <= seq <= facts['total']
                or source.state == 'conflict' or other.get('status') not in ('POSTED', 'PENDING')
                or any(other.get(k) != facts.get(k) for k in
                       ['total', 'payment_type', 'direction', 'operation', 'purchase_date', 'last_four', 'currency'])
                or abs(abs(money(other['amount'])) - abs(money(facts['amount']))) > tolerance):
            return []
        sequences.add(seq)
        try:
            due = payment_due_date(source)
        except ValidationError:
            return []
        if due:
            cycles.add(due.year * 12 + due.month - seq)
    return rows if len(cycles) <= 1 else []


@transaction.atomic
def attach_installment_group(row, target):
    facts = row.facts
    total, sequence = facts.get('total'), facts.get('number')
    if (facts.get('payment_type') != 'INSTALLMENT' or type(total) is not int or type(sequence) is not int
            or not 1 <= sequence <= total <= 120 or target.paid != sequence
            or abs(target.installments_number or 0) != total):
        return None
    user = row.account.connection.user
    if target.user_id != user.pk or target.card_id != row.account.card_id:
        raise ValidationError('O parcelamento deve pertencer ao mesmo usuário e cartão.')
    bundle = installment_bundle(row)
    linked = []
    for source in bundle:
        local = source.transaction
        if not local:
            continue
        if (local.user_id != user.pk or local.card_id != target.card_id
                or local.card_number_id != target.card_number_id
                or local.paid != source.facts['number'] or abs(local.installments_number or 0) != total):
            return target.installment
        linked.append(local)
    existing = {t.installment_id for t in linked if t.installment_id}
    if len(existing) > 1 or (target.installment_id and existing and target.installment_id not in existing):
        return target.installment
    plan = target.installment
    if not plan and len(existing) == 1:
        plan = Installment.objects.get(pk=next(iter(existing)), user=user)
    if not plan:
        plan = Installment.objects.create(user=user, description=target.description[:50], posted_date=target.posted_date)
    if plan.user_id != user.pk:
        raise ValidationError('Parcelamento de outro usuário.')
    # A fingerprint with repeated sequence numbers is ambiguous: keep a separate plan.
    members = linked if bundle else [target]
    if target.pk not in {t.pk for t in members}:
        members.append(target)
    Transaction.objects.filter(user=user, pk__in=[t.pk for t in members]).update(installment=plan, installments_number=total)
    anchors = [s.pk for s in bundle] if bundle else [row.pk]
    # Materialize before UPDATE: the ownership join reads statement_transaction,
    # which MySQL forbids inside a subquery updating that same table (1093).
    projected_ids = list(
        ProjectedInstallment.objects.filter(
            anchor_id__in=anchors, transaction__user=user, account=row.account
        ).values_list('transaction_id', flat=True)
    )
    Transaction.objects.filter(user=user, pk__in=projected_ids).update(installment=plan)
    target.installment = plan
    target.installments_number = total
    return plan
