"""Link existing records after a complete collection. Never creates money flows."""
from collections import Counter
from decimal import Decimal, InvalidOperation
import re
import unicodedata

from django.core.exceptions import ValidationError
from django.utils import timezone

from bank_sync.cash_reviews import bank_rows, candidates, review_cash
from bank_sync.investment_events import classify, event_date, legacy_link_candidates, operation_for, reconcile
from bank_sync.models import (BankConnection, ExternalInvestment, InvestmentCashEvidence,
                             InvestmentCashReview, InvestmentEvent, InvestmentHistoryJob)
from investments.models import InvestmentTransaction as Movement
from investments.services.transaction import InvestmentTransactionService as Service
from investments.events import investment_atomic, mark_changed


def amount(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() and result > 0 else None


def text(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value or '').lower())
                   if not unicodedata.combining(c))


def family(description):
    return set(re.findall(r'\b(?:cdb|lci|lca)\b', text(description)))


def unused(movement):
    return not movement.reconciled_operations.exists() and not movement.bank_cash_reviews.exists()


def operation_rows(user, primary, require_pair=False):
    if not primary.operation_id:
        return None if require_pair else [primary]
    rows = list(Movement.objects.filter(user=user, investment__user=user,
                                        operation_id=primary.operation_id).select_related('investment'))
    # No guessed grouping of unrelated entries sharing a legacy UUID.
    others = [m for m in rows if m.pk != primary.pk]
    if (len(others) != 1 or others[0].investment.default_wallet_for_id != user.pk
            or others[0].amount != primary.amount or others[0].date != primary.date
            or {others[0].type, primary.type} != {'aporte', 'resgate'}
            or any(not unused(m) for m in rows)):
        return None
    return rows


def matching_cash(connection, event, source):
    net = amount(event.facts.get('netAmount'))
    if net is None:
        return []
    kind = classify(event.facts)[0]
    direction = 'DEBIT' if kind == 'buy' else 'CREDIT'
    matches = []
    for cash in InvestmentCashEvidence.objects.filter(
        connection=connection, operations__isnull=True, reviews__isnull=True,
        facts__status='POSTED', facts__currencyCode='BRL', facts__type=direction,
    ):
        if cash.revision != 1 or cash.history:
            continue
        description = text(cash.facts.get('description'))
        investment = source.investment
        if investment.asset.asset_type == 'fixed_income':
            known = family(investment.description + ' ' + investment.asset.description + ' ' + str(source.facts.get('name', '')))
            if (not description.startswith('aplicacao - ' if kind == 'buy' else 'resgate - ')
                    or not family(description).intersection(known)):
                continue
        elif investment.asset.asset_type == 'variable_income':
            if not description.startswith('debito b3 - ' if kind == 'buy' else 'credito b3 - '):
                continue
        else:
            continue
        try:
            signed = amount(cash.facts.get('amount') if direction == 'CREDIT' else
                            -Decimal(str(cash.facts.get('amount', 0))))
        except InvalidOperation:
            continue
        if signed == net and event_date(cash.facts) == event_date(event.facts):
            matches.append(cash)
    return matches


def event_proposal(connection, event):
    if event.state not in ('new', 'historical') or event.revision != 1 or operation_for(event):
        return None
    sources = list(event.investments.select_related('investment__asset').filter(connection=connection))
    if len(sources) != 1 or not sources[0].investment_id:
        return None
    investment = sources[0].investment
    if investment.user_id != connection.user_id or investment.asset.currency != 'BRL':
        return None
    kind = classify(event.facts)[0]
    net, gross = amount(event.facts.get('netAmount')), amount(event.facts.get('amount'))
    if (kind not in ('buy', 'sell') or net is None or gross is None
            or event.facts.get('priceFactor') not in (None, 1, '1')):
        return None
    # Fee splits and ambiguous proventos stay manual unless already linked by the importer.
    if kind in ('buy', 'income') and net != gross:
        return None
    if kind == 'sell' and gross < net:
        return None
    when = event_date(event.facts)
    types = {'buy': 'aporte', 'sell': 'resgate', 'income': 'rendimento'}
    rows = list(Movement.objects.filter(user=connection.user, investment=investment,
                                        date=when, type=types[kind], amount=net))
    legacy = list(legacy_link_candidates(connection.user, event, investment).filter(date=when))
    legacy_ids = {m.pk for m in legacy}
    rows.extend(m for m in legacy if m.pk not in {row.pk for row in rows})
    valid = []
    for movement in rows:
        if not unused(movement):
            continue
        if kind in ('buy', 'sell'):
            units = amount(event.facts.get('quantity'))
            if units is None or (movement.quantity != units and
                                 not (movement.pk in legacy_ids and movement.quantity is None)):
                continue
        members = operation_rows(connection.user, movement, require_pair=True)
        if members:
            valid.append((movement, members))
    cash = matching_cash(connection, event, sources[0])
    if len(valid) != 1 or len(cash) != 1:
        return None
    primary, members = valid[0]
    return {'event': event, 'cash': cash[0], 'primary': primary, 'members': members}


def bank_proposal(connection, cash):
    # Description, custody, exact date, unique amount AND a balanced wallet pair.
    # Matching just an amount is never enough.
    if cash.revision != 1 or cash.reviews.exists() or cash.history:
        return None
    description = text(cash.facts.get('description'))
    wanted = family(description)
    stock = description.startswith('debito b3 - ')
    if not wanted and not stock:
        return None
    mapped = ExternalInvestment.objects.filter(connection=connection, investment__user=connection.user)
    brokers = set(mapped.values_list('investment__broker_id', flat=True))
    possible = []
    for movement in candidates(connection.user, cash).filter(date=event_date(cash.facts)):
        investment = movement.investment
        if (investment.broker_id not in brokers or investment.asset.currency != 'BRL'
                or not unused(movement)):
            continue
        # A broker mapped to another connection makes the bank account ambiguous.
        if ExternalInvestment.objects.filter(connection__user=connection.user,
                investment__broker_id=investment.broker_id).exclude(connection=connection).exists():
            continue
        known = family(investment.description + ' ' + investment.asset.description + ' ' + investment.asset.symbol)
        if stock:
            if investment.asset.asset_type != 'variable_income' or not mapped.filter(investment=investment).exists():
                continue
        elif investment.asset.asset_type != 'fixed_income' or not wanted.intersection(known):
            continue
        members = operation_rows(connection.user, movement, require_pair=True)
        if members:
            possible.append(movement)
    return possible[0] if len(possible) == 1 else None


def reserved_by_event(connection, movement):
    kind = 'BUY' if movement.type == 'aporte' else 'SELL'
    for event in InvestmentEvent.objects.filter(
        connection=connection, state__in=['new', 'historical', 'conflict', 'ignored'], facts__type=kind,
    ):
        if amount(event.facts.get('netAmount')) != movement.amount or event_date(event.facts) != movement.date:
            continue
        for source in event.investments.select_related('investment__asset').filter(connection=connection):
            if source.investment_id == movement.investment_id:
                return True
            if source.investment_id and legacy_link_candidates(connection.user, event, source.investment).filter(pk=movement.pk).exists():
                return True
    return False


@investment_atomic()
def auto_reconcile(connection, *, job=None, lease_token=None, dry_run=False):
    Service.lock_user(connection.user)
    connection = BankConnection.objects.select_for_update().get(pk=connection.pk)
    latest = InvestmentHistoryJob.objects.filter(connection=connection).order_by('-id').first()
    if (not latest or latest.state != 'succeeded' or (job and latest.pk != job.pk)
            or InvestmentHistoryJob.objects.filter(connection=connection, state__in=['queued', 'running']).exists()):
        raise ValidationError('Conclua uma coleta completa antes dos vínculos automáticos.')
    if connection.lease_until and connection.lease_until > timezone.now() and connection.lease_token != lease_token:
        raise ValidationError('A conexão está sendo consultada; aguarde para conciliar.')
    proposals = []
    for event in InvestmentEvent.objects.filter(connection=connection, last_seen_job=latest,
                                                 state__in=['new', 'historical']).order_by('pk'):
        proposal = event_proposal(connection, event)
        if proposal:
            proposals.append(proposal)
    movements = Counter(p['primary'].pk for p in proposals)
    cash_ids = Counter(p['cash'].pk for p in proposals)
    links = []
    used_cash, used_movements = set(), set()
    for p in proposals:
        if movements[p['primary'].pk] != 1 or cash_ids[p['cash'].pk] != 1:
            continue
        # Another unresolved event for this title/date/value could be the same operation.
        competitors = InvestmentEvent.objects.filter(
            connection=connection, state__in=['new', 'historical', 'conflict'],
            investments__in=p['event'].investments.all(),
            facts__type=p['event'].facts.get('type'),
        ).exclude(pk=p['event'].pk)
        if any(event_date(e.facts) == event_date(p['event'].facts) and
               amount(e.facts.get('netAmount')) == amount(p['event'].facts.get('netAmount')) for e in competitors):
            continue
        evidence = (f'Vínculo automático: evento {p["event"].external_id}; título ou origem consolidada documentada; '
                    f'mesma data e valor líquido; comprovante {p["cash"].external_id}; '
                    f'lançamentos {", ".join(str(m.pk) for m in p["members"])}. Nenhum saldo alterado.')
        if not dry_run:
            op = reconcile(connection.user, p['event'].pk, p['event'].revision, 'link',
                           movement_ids=[m.pk for m in p['members']], cash_ids=[p['cash'].pk], evidence=evidence)
            op.automatic = True
            op.save(update_fields=['automatic'])
        links.append({'event_id': p['event'].pk, 'cash_id': p['cash'].pk,
                      'movement_ids': [m.pk for m in p['members']]})
        used_cash.add(p['cash'].pk)
        used_movements.update(m.pk for m in p['members'])
    bank = []
    for cash in bank_rows(connection.user).filter(connection=connection, reviewed=False).exclude(pk__in=used_cash):
        movement = bank_proposal(connection, cash)
        if movement and movement.pk not in used_movements:
            bank.append((cash, movement))
    counts = Counter(m.pk for _, m in bank)
    reviews = []
    for cash, movement in bank:
        if counts[movement.pk] != 1:
            continue
        # Do not take a movement that an unresolved investment event may need.
        if any(p['primary'].pk == movement.pk for p in proposals) or reserved_by_event(connection, movement):
            continue
        if not dry_run:
            review_cash(connection.user, cash.pk, cash.revision, 'link', movement.pk,
                        'Vínculo automático: mesmo banco, tipo de ativo, data e valor; '
                        f'par de caixa documentado {movement.operation_id}. Nenhum saldo alterado.', automatic=True)
        reviews.append({'cash_id': cash.pk, 'movement_id': movement.pk})
    if not dry_run and (links or reviews):
        mark_changed(connection.user_id)
    return {'events': links, 'bank_entries': reviews}
