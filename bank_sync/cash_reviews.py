"""Document bank-only evidence without inventing investment transactions."""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import BooleanField, Case, Exists, F, OuterRef, Q, Value, When

from bank_sync.models import ExternalInvestment, InvestmentCashEvidence, InvestmentCashReview
from bank_sync.investment_events import event_date
from investments.models import InvestmentTransaction as Movement
from investments.services.transaction import InvestmentTransactionService as Service


def bank_rows(user):
    reviewed = InvestmentCashReview.objects.filter(cash_id=OuterRef('pk'), revision=OuterRef('revision')).exclude(
        action='apply', trade__state='conflict',
    )
    prior = Q(pk__in=[])
    for connection_id in user.bankconnection_set.values_list('pk', flat=True):
        sources = list(ExternalInvestment.objects.filter(
            connection_id=connection_id, investment__user=user, investment__asset__currency='BRL',
        ).select_related('investment__reconciliation_baseline'))
        baselines = [getattr(s.investment, 'reconciliation_baseline', None) for s in sources]
        if baselines and all(baselines):
            cutoff = min(b.date for b in baselines)
            prior |= Q(connection_id=connection_id, facts__date__lt=(cutoff + timedelta(days=1)).isoformat())
    return InvestmentCashEvidence.objects.filter(
        connection__user=user, operations__isnull=True,
        facts__status='POSTED', facts__currencyCode='BRL',
    ).filter(
        Q(facts__type='CREDIT', facts__description__istartswith='Resgate - ')
        | Q(facts__type='DEBIT', facts__description__istartswith='Aplicação - ')
        | Q(facts__type='DEBIT', facts__description__istartswith='Compra - Criptomoedas')
        | Q(facts__type='DEBIT', facts__description__istartswith='Débito B3 - ')
    ).annotate(reviewed=Exists(reviewed), prior_to_baseline=Case(
        When(prior, then=Value(True)), default=Value(False), output_field=BooleanField(),
    ))


def candidates(user, cash):
    when = event_date(cash.facts)
    try:
        amount = Decimal(str(cash.facts['amount']))
    except (InvalidOperation, KeyError):
        raise ValidationError('Valor inválido no comprovante.') from None
    if not amount.is_finite() or not amount or (amount > 0) != (cash.facts['type'] == 'CREDIT'):
        raise ValidationError('Valor ou direção inválida no comprovante.')
    return Movement.objects.filter(
        user=user, investment__user=user, amount=abs(amount),
        type='resgate' if amount > 0 else 'aporte',
        date__range=(when - timedelta(days=7), when + timedelta(days=7)),
    ).exclude(investment__default_wallet_for=user).select_related('investment', 'investment__broker')


@transaction.atomic
def review_cash(user, pk, revision, action, movement_id=None, evidence='', *, automatic=False):
    Service.lock_user(user)
    cash = InvestmentCashEvidence.objects.select_for_update().get(pk=pk, connection__user=user)
    if cash.revision != revision:
        raise ValidationError('O comprovante mudou; confira a versão atual.')
    existing = cash.reviews.filter(revision=revision).first()
    if existing:
        raise ValidationError('Esta versão já foi conferida. Recarregue a lista.')
    if not bank_rows(user).filter(pk=pk, reviewed=False).exists():
        raise ValidationError('Este comprovante não está disponível para conferência.')
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValidationError('Descreva a correspondência ou por que o valor já está incluído no histórico.')
    if action not in ('link', 'covered'):
        raise ValidationError('Ação inválida.')
    movement = None
    if action == 'link':
        movement = candidates(user, cash).filter(pk=movement_id).first()
        if not movement:
            raise ValidationError('Escolha um lançamento próprio com mesmo valor, sentido e data próxima.')
        used = InvestmentCashReview.objects.filter(
            revision=F('cash__revision'), movements=movement,
        )
        # A movement cannot explain two independent bank entries.
        if used.exists():
            raise ValidationError('Este lançamento já foi vinculado a outro comprovante.')
    review = InvestmentCashReview.objects.create(
        cash=cash, revision=revision, action=action, evidence=evidence.strip(), automatic=automatic,
    )
    if movement:
        review.movements.add(movement)
    return review
