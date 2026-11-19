"""Import complete post-opening events; missing facts remain explicit exceptions."""
from collections import Counter
from decimal import Decimal
import hashlib
import json
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from bank_sync.auto_reconciliation import amount, matching_cash, text
from bank_sync.investment_events import classify, event_date, operation_for, reconcile
from bank_sync.investments import normalize
from bank_sync.models import (BankConnection, ExternalInvestment, InvestmentBankTrade, InvestmentCashEvidence,
                             InvestmentEvent, InvestmentHistoryJob, InvestmentSnapshot)
from clients.pluggy.reader import ProbeError
from investments.events import investment_atomic, mark_changed
from investments.models import Asset, Broker, Investment, InvestmentTransaction as Movement
from investments.services.investment import InvestmentService
from investments.services.transaction import InvestmentTransactionService as Service

D = lambda value: Decimal(str(value))


def funding(user, net, when):
    credits = []
    for credit in Movement.objects.filter(user=user, investment__default_wallet_for=user,
            type__in=['aporte', 'rendimento'], date__lte=when).prefetch_related('cash_allocations_out', 'funded_transactions'):
        used = sum((m.amount for m in credit.funded_transactions.all()), D(0))
        used += sum((a.amount for a in credit.cash_allocations_out.all()), D(0))
        available = credit.amount - used
        if available >= net:
            credits.append((credit, available))
    exact = [c for c, value in credits if value == net]
    if len(exact) == 1:
        return [{'credit_id': exact[0].pk, 'amount': str(net)}]
    if len(credits) == 1:
        return [{'credit_id': credits[0][0].pk, 'amount': str(net)}]
    raise ValidationError('Há mais de uma origem possível, ou falta saldo de caixa registrado para esta compra.')


def income_cash(connection, event):
    rows = []
    for cash in InvestmentCashEvidence.objects.filter(connection=connection, operations__isnull=True,
            reviews__isnull=True, revision=1, facts__type='CREDIT', facts__status='POSTED', facts__currencyCode='BRL'):
        description = text(cash.facts.get('description'))
        if (cash.history or not any(word in description for word in ['evento b3', 'dividendo', 'juros', 'rendimento'])
                or event_date(cash.facts) != event_date(event.facts)
                or amount(cash.facts.get('amount')) != amount(event.facts.get('netAmount'))):
            continue
        rows.append(cash)
    return rows


def can_adopt(event, source, trade):
    kind = classify(event.facts)[0]
    cash = trade.credit if kind == 'sell' else trade.debit
    if (source.facts.get('currencyCode') != 'BRL' or trade.state != 'applied'
            or cash.revision != (trade.credit_revision if kind == 'sell' else trade.debit_revision)
            or event_date(event.facts) != event_date(cash.facts)
            or amount(event.facts.get('netAmount')) != trade.amount or cash.operations.exists()):
        return None
    review = cash.reviews.filter(action='apply', trade=trade, revision=cash.revision).first()
    if not review:
        return None
    primary = list(review.movements.filter(type='resgate' if kind == 'sell' else 'aporte',
        investment=trade.source.investment if kind == 'sell' else trade.investment, amount=trade.amount))
    if len(primary) != 1 or amount(event.facts.get('quantity')) != primary[0].quantity:
        return None
    if kind == 'sell' and source.pk != trade.source_id:
        return None
    if kind == 'buy':
        if source.investment_id not in (None, trade.investment_id):
            return None
        if not source.investment_id:
            name = text(source.facts.get('name'))
            asset = trade.investment.asset
            if source.facts.get('type') not in ('CRYPTO', 'CRYPTOCURRENCY') or not (
                text(asset.symbol) in name.split() or text(asset.description) == name
                or (asset.symbol == 'BTC' and name == 'bitcoin')):
                return None
    return cash, review


def adopt_bank_trade(connection, event, source):
    kind = classify(event.facts)[0]
    if kind not in ('buy', 'sell'):
        return False
    matches = []
    for trade in InvestmentBankTrade.objects.filter(debit__connection=connection, state='applied').select_related(
            'credit', 'debit', 'source__investment', 'investment__asset'):
        match = can_adopt(event, source, trade)
        if match:
            matches.append((trade, *match))
    if len(matches) != 1:
        return False
    trade, cash, review = matches[0]
    if source.investment_id is None:
        if ExternalInvestment.objects.filter(investment=trade.investment).exists():
            return False
        source.investment = trade.investment
        source.save(update_fields=['investment'])
    op = reconcile(connection.user, event.pk, event.revision, 'link',
        movement_ids=list(review.movements.values_list('pk', flat=True)), cash_ids=[cash.pk],
        evidence='Evento recebido após registro bancário da mesma operação; valor, quantidade e liquidação idênticos.')
    op.automatic = True
    op.save(update_fields=['automatic'])
    trade.journal.setdefault('source_events', []).append({'event_id': event.pk, 'revision': event.revision})
    trade.save(update_fields=['journal'])
    mark_changed(connection.user_id)
    return True


def bootstrap(connection, source, event):
    facts = source.facts
    when = event_date(event.facts)
    name = str(facts.get('name') or '').strip()
    equity = facts.get('type') == 'EQUITY' and bool(re.fullmatch('[A-Z]{4}[0-9]{1,2}', name))
    fixed = facts.get('type') == 'FIXED_INCOME'
    if (classify(event.facts)[0] != 'buy' or not (fixed or equity)
            or facts.get('currencyCode') != 'BRL' or facts.get('status') != 'ACTIVE'
            or amount(event.facts.get('quantity')) != amount(facts.get('quantity'))
            or source.investmentevent_set.exclude(pk=event.pk).exists()):
        raise ValidationError('O novo título precisa de aquisição e posição completas para cadastro automático.')
    acquired = parse_datetime(facts.get('purchaseDate') or '')
    if (fixed and not acquired) or (acquired and acquired.date() != when):
        raise ValidationError('A data de aquisição do novo título não está confirmada.')
    linked = ExternalInvestment.objects.filter(connection=connection, investment__user=connection.user)
    cutoff = linked.order_by('-investment__reconciliation_baseline__date').values_list(
        'investment__reconciliation_baseline__date', flat=True).first()
    if cutoff and when <= cutoff:
        raise ValidationError('Título anterior à abertura auditada exige reconstrução histórica.')
    brokers = set(linked.values_list('investment__broker_id', flat=True))
    if len(brokers) != 1:
        raise ValidationError('Identifique a instituição do novo título antes de importá-lo.')
    if not Broker.objects.filter(pk=next(iter(brokers)), user=connection.user).exists():
        raise ValidationError('A instituição não pertence ao proprietário da conexão.')
    normalized, reference = normalize({'id': str(source.external_id), **facts})
    if reference.date() < when:
        raise ValidationError('A posição do novo título é anterior à aquisição.')
    if not name or len(name) > 120:
        raise ValidationError('Nome do título ausente ou inválido.')
    asset_type = 'variable_income' if equity else 'fixed_income'
    symbol = name if equity else ''
    asset, _ = Asset.objects.get_or_create(user=connection.user, description=name, symbol=symbol,
        defaults={'asset_type': asset_type, 'currency': 'BRL', 'income_behavior': 'dividend' if equity else 'interest'})
    if asset.asset_type != asset_type or asset.currency != 'BRL':
        raise ValidationError('O ativo existente tem classificação diferente da posição recebida.')
    try:
        due = parse_datetime(facts['dueDate']) if facts.get('dueDate') else None
    except ValueError:
        raise ValidationError('A data de vencimento do título é inválida.') from None
    inv = Investment.objects.create(user=connection.user, asset=asset, broker_id=next(iter(brokers)),
        description=f'{name} · {when.isoformat()}', start_date=when,
        due_date=due.date() if due else None,
        notes=f'Cadastro pela integração. Identificador externo: {source.external_id}')
    source.investment = inv
    source.save(update_fields=['investment'])
    return normalized, reference


def sell_principal(source, event):
    when = event_date(event.facts)
    for old in source.investmentevent_set.exclude(pk=event.pk):
        if old.facts.get('type') != 'SELL' or event_date(old.facts) > when:
            continue
        op = operation_for(old)
        if op and op.kind == 'income':
            continue
        if (not op or op.state not in ('applied', 'linked')
                or not op.movements.filter(investment=source.investment, type='resgate',
                    quantity=old.facts.get('quantity'), redemption_principal__isnull=False).exists()):
            raise ValidationError('Um resgate anterior ainda não está refletido no custo deste título.')
    quote_ids = list(source.investment.transactions.filter(type='atualizacao', date__gte=when).values_list('pk', flat=True))
    position = InvestmentService.get_position(source.investment, as_of=when, exclude_ids=quote_ids)
    units = amount(event.facts.get('quantity'))
    if (units is None or position['quantity'] < units or position['remaining_principal'] <= 0
            or source.investment.transactions.filter(type='aporte', quantity__isnull=True).exists()):
        raise ValidationError('O custo e a quantidade da parcela vendida não estão completos.')
    return (position['remaining_principal'] * units / position['quantity']).quantize(D('.01'))


@investment_atomic()
def import_events(connection, *, job=None, lease_token=None):
    Service.lock_user(connection.user)
    connection = BankConnection.objects.select_for_update().get(pk=connection.pk)
    latest = InvestmentHistoryJob.objects.filter(connection=connection).order_by('-id').first()
    if (not latest or latest.state != 'succeeded' or (job and latest.pk != job.pk)
            or InvestmentHistoryJob.objects.filter(connection=connection, state__in=['queued', 'running']).exists()
            or (connection.lease_until and connection.lease_until > timezone.now() and connection.lease_token != lease_token)):
        raise ValidationError('Aguarde uma coleta completa antes de importar eventos.')
    from bank_sync.bank_trades import flag_bank_trade_conflicts
    flag_bank_trade_conflicts(connection)
    pending = list(InvestmentEvent.objects.filter(connection=connection, last_seen_job=latest,
        state='new', revision=1).prefetch_related('investments__investment__asset'))
    pending.sort(key=lambda e: (event_date(e.facts), {'income': 0, 'sell': 1, 'buy': 2}.get(classify(e.facts)[0], 3), e.pk))
    applied, adopted = [], []
    for event in pending:
        if operation_for(event) or classify(event.facts)[0] not in ('buy', 'sell', 'income'):
            continue
        sources = list(event.investments.filter(connection=connection).select_related('investment__asset'))
        if len(sources) != 1:
            continue
        source = sources[0]
        if source.facts.get('currencyCode') != 'BRL':
            continue
        if source.investment_id and (source.investment.user_id != connection.user_id
                or source.investment.asset.user_id != connection.user_id
                or source.investment.broker.user_id != connection.user_id):
            continue
        try:
            with transaction.atomic():
                # The bank-only fallback may already have recorded this event before the provider supplied it.
                if adopt_bank_trade(connection, event, source):
                    adopted.append(event.pk)
                    continue
                kind = classify(event.facts)[0]
                net, gross = amount(event.facts.get('netAmount')), amount(event.facts.get('amount'))
                if net is None or gross is None or event.facts.get('priceFactor') not in (None, 1, '1'):
                    raise ValidationError('Valores ou fator de preço incompletos para importação automática.')
                when = event_date(event.facts)
                inv = source.investment
                allocations = funding(connection.user, net, when) if kind == 'buy' else []
                new_quote = bootstrap(connection, source, event) if not inv else None
                inv = source.investment
                baseline = getattr(inv, 'reconciliation_baseline', None)
                if inv.asset.currency != 'BRL' or (baseline and when <= baseline.date) or when < inv.start_date:
                    raise ValidationError('Evento histórico ou em moeda estrangeira exige revisão.')
                expected = {'buy': 'aporte', 'sell': 'resgate', 'income': 'rendimento'}[kind]
                if inv.transactions.filter(type=expected, amount__in=[net, gross], date=when).exists():
                    raise ValidationError('Já existe lançamento semelhante; confira o vínculo antes de importar.')
                cash = income_cash(connection, event) if kind == 'income' else matching_cash(connection, event, source)
                if len(cash) != 1:
                    raise ValidationError('Falta uma liquidação bancária única com mesmo valor, tipo e data.')
                # Do not consume a bank receipt disputed by another source event.
                competitors = [e for e in pending if e.pk != event.pk and not operation_for(e)
                    and classify(e.facts)[0] == kind and event_date(e.facts) == when
                    and amount(e.facts.get('netAmount')) == net]
                if competitors:
                    raise ValidationError('Há mais de um evento compatível com a liquidação bancária.')
                principal = sell_principal(source, event) if kind == 'sell' else None
                op = reconcile(connection.user, event.pk, event.revision, 'apply', cash_ids=[cash[0].pk],
                    allocations=allocations, principal=principal,
                    evidence='Importação automática: evento da instituição, liquidação bancária e origem de caixa/custo documentados.')
                op.automatic = True
                op.save(update_fields=['automatic'])
                if new_quote:
                    facts, reference = new_quote
                    movement = Movement.objects.create(user=connection.user, investment=inv,
                        date=max(when, reference.date()), type='atualizacao', current_value=D(facts['balance']),
                        quantity=D(facts['quantity']), notes='Posição oficial após cadastro automático do título.')
                    fingerprint = hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()
                    InvestmentSnapshot.objects.create(external=source, reference_at=reference, fingerprint=fingerprint,
                                                        facts=facts, movement=movement)
                    source.reference_at = reference
                    source.facts = facts
                    source.save(update_fields=['facts', 'reference_at'])
                applied.append(event.pk)
        except (ValidationError, ProbeError) as error:
            InvestmentEvent.objects.filter(pk=event.pk, state='new').update(
                reason=' '.join(error.messages) if isinstance(error, ValidationError) else str(error))
    if applied or adopted:
        mark_changed(connection.user_id)
    return {'applied': applied, 'adopted': adopted}
