"""Create a documented redemption → wallet → crypto purchase from bank evidence."""
from decimal import Decimal, InvalidOperation
import json
import re
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from bank_sync.models import (BankConnection, ExternalInvestment, InvestmentBankTrade, InvestmentCashEvidence,
                             InvestmentCashReview, InvestmentHistoryJob, InvestmentEvent, ReconciledInvestmentOperation)
from bank_sync.investment_events import event_date, legacy_link_candidates, operation_for
from investments.events import investment_atomic
from investments.models import Asset, Investment, InvestmentTransaction as Movement
from investments.services.investment import InvestmentService
from investments.services.transaction import InvestmentTransactionService as Service

D = lambda value: Decimal(str(value))


def positive(value):
    try:
        value = D(value)
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError('Valor ou quantidade inválida.') from None
    if not value.is_finite() or value <= 0:
        raise ValidationError('Valor ou quantidade deve ser positivo.')
    return value


def complete(connection):
    latest = InvestmentHistoryJob.objects.filter(connection=connection).order_by('-id').first()
    if not latest or latest.state != 'succeeded':
        raise ValidationError('Conclua uma consulta completa antes de registrar a operação.')
    if connection.lease_until and connection.lease_until > timezone.now():
        raise ValidationError('A conexão está sendo atualizada. Aguarde.')


def receipt(cash, kind, *, registered=False):
    if (cash.facts.get('status') != 'POSTED' or cash.facts.get('currencyCode') != 'BRL'
            or cash.facts.get('type') != kind or cash.revision != 1 or cash.history
            or (not registered and (cash.operations.exists() or cash.reviews.exists()))):
        raise ValidationError('O comprovante foi usado, revisado ou não está efetivado em reais.')
    value = D(cash.facts.get('amount', 0))
    return positive(value if kind == 'CREDIT' else -value)


def registered_source_plan(credit):
    operations = list(credit.operations.filter(kind='sell', state='applied').select_related('event'))
    if len(operations) != 1:
        return None
    op = operations[0]
    net = receipt(credit, 'CREDIT', registered=True)
    sources = list(op.event.investments.filter(connection=credit.connection, investment__user=credit.connection.user))
    if len(sources) != 1 or not sources[0].investment_id:
        return None
    source = sources[0]
    funding = list(op.movements.filter(type='aporte', investment__default_wallet_for=credit.connection.user,
                                      amount=net, date=event_date(credit.facts)))
    redemptions = list(op.movements.filter(type='resgate', investment=source.investment,
                                          amount=net, redemption_principal__isnull=False))
    if len(funding) != 1 or len(redemptions) != 1 or not redemptions[0].quantity:
        return None
    funding = funding[0]
    used = sum((m.amount for m in funding.funded_transactions.all()), D(0))
    used += sum((m.amount for m in funding.cash_allocations_out.all()), D(0))
    if funding.amount - used < net:
        return None
    return {'source': source, 'funding': funding, 'principal': redemptions[0].redemption_principal,
            'quantity': redemptions[0].quantity, 'changes': [], 'recognized': [], 'involved': {source.investment_id},
            'proofs': [{'event_id': op.event_id, 'revision': op.event.revision}],
            'opening_operation': None, 'source_operation': op}


def source_plan(source, credit):
    """Only a complete, single-lot fixed-income chain can prove a bank-only final sale."""
    inv = source.investment
    when = event_date(credit.facts)
    if (not inv or inv.user_id != credit.connection.user_id or inv.asset.user_id != inv.user_id
            or inv.broker.user_id != inv.user_id or inv.asset.currency != 'BRL'
            or inv.asset.asset_type != 'fixed_income' or source.facts.get('status') != 'TOTAL_WITHDRAWAL'
            or D(source.facts.get('balance', -1)) != 0 or D(source.facts.get('quantity', -1)) != 0
            or not source.reference_at or source.reference_at.date() != when):
        raise ValidationError('A origem precisa ter resgate total confirmado na mesma data.')
    from bank_sync.auto_reconciliation import family
    if not family(credit.facts.get('description')).intersection(family(source.facts.get('name', '') + ' ' + inv.asset.description)):
        raise ValidationError('O tipo do resgate não corresponde ao título de origem.')
    events = list(source.investmentevent_set.order_by('facts__date', 'id'))
    buys = [e for e in events if e.facts.get('type') == 'BUY']
    all_sales = [e for e in events if e.facts.get('type') == 'SELL']
    sales = [e for e in all_sales if event_date(e.facts) < when]
    final_events = [e for e in all_sales if event_date(e.facts) == when]
    if (len(buys) != 1 or len(buys) + len(all_sales) != len(events) or len(final_events) > 1
            or any(event_date(e.facts) > when for e in all_sales)):
        raise ValidationError('O histórico da origem ainda não permite determinar o custo sem estimativa.')
    buy = buys[0]
    cost = positive(buy.facts.get('netAmount'))
    units = positive(buy.facts.get('quantity'))
    buy_date = event_date(buy.facts)
    purchase_date = parse_datetime(source.facts.get('purchaseDate') or '')
    buy_op = operation_for(buy)
    if (buy.revision != 1 or buy.state not in ('linked', 'applied') or not buy_op
            or buy_op.state not in ('linked', 'applied') or D(buy.facts.get('amount', 0)) != cost
            or buy.facts.get('priceFactor') not in (None, 1, '1')
            or not purchase_date or purchase_date.date() != buy_date or buy_date >= when):
        raise ValidationError('A aquisição de origem precisa estar documentada e conciliada.')
    opening = list(buy_op.movements.filter(investment=inv, type='aporte', amount=cost, quantity=units))
    if len(opening) != 1:
        raise ValidationError('A aquisição não corresponde a um único lançamento de origem.')
    opening = opening[0]
    opening_rows = list(buy_op.movements.all())
    cash_buy = list(buy_op.cash_evidence.all())
    if (len(cash_buy) != 1 or cash_buy[0].revision != 1 or cash_buy[0].facts.get('status') != 'POSTED'
            or cash_buy[0].facts.get('currencyCode') != 'BRL' or cash_buy[0].facts.get('type') != 'DEBIT'
            or D(cash_buy[0].facts.get('amount', 0)) != -cost or event_date(cash_buy[0].facts) != buy_date):
        raise ValidationError('Falta o débito bancário que comprova a aquisição original.')
    changes = []
    allowed = {opening.pk}
    involved = {inv.pk}
    baseline = getattr(inv, 'reconciliation_baseline', None)
    if opening.date != buy_date:
        if (not baseline or opening.date != baseline.date or len(opening_rows) != 2
                or not opening.operation_id):
            raise ValidationError('A data da abertura precisa de revisão documental.')
        other = next(m for m in opening_rows if m.pk != opening.pk)
        if (other.type != 'resgate' or other.amount != cost or other.date != opening.date
                or other.operation_id != opening.operation_id or other.user_id != inv.user_id
                or other.investment.broker_id != inv.broker_id or other.investment.default_wallet_for_id):
            raise ValidationError('A reclassificação da abertura não está documentada.')
        involved.add(other.investment_id)
        changes.extend([(opening, {'date': buy_date}), (other, {'date': buy_date})])
    remaining_units, remaining_cost = units, cost
    recognized = []
    for event in sales:
        op = operation_for(event)
        day = event_date(event.facts)
        qty, net, gross = (positive(event.facts.get(key)) for key in ('quantity', 'netAmount', 'amount'))
        if (event.revision != 1 or event.state not in ('linked', 'applied') or not op
                or op.state not in ('linked', 'applied') or not buy_date <= day < when
                or event.facts.get('priceFactor') not in (None, 1, '1') or qty > remaining_units or gross < net):
            raise ValidationError('Há resgates anteriores ainda sem custo e quantidade comprovados.')
        taxes = sum((D(v) for v in (event.facts.get('expenses') or {}).values() if v is not None), D(0))
        if taxes != gross - net:
            raise ValidationError('As despesas do resgate anterior não correspondem à liquidação.')
        proof = list(op.cash_evidence.all())
        if (len(proof) != 1 or proof[0].revision != 1 or proof[0].facts.get('type') != 'CREDIT'
                or proof[0].facts.get('status') != 'POSTED' or proof[0].facts.get('currencyCode') != 'BRL'
                or D(proof[0].facts.get('amount', 0)) != net or event_date(proof[0].facts) != day):
            raise ValidationError('Falta comprovação bancária de um resgate anterior.')
        rows = list(op.movements.select_related('investment'))
        debits = [m for m in rows if m.type == 'resgate' and m.amount == net and m.date == day
                  and m.investment.default_wallet_for_id is None]
        credits = [m for m in rows if m.type == 'aporte' and m.amount == net and m.date == day
                   and m.investment.default_wallet_for_id == inv.user_id]
        if len(debits) != 1 or len(credits) != 1 or len(rows) != 2:
            raise ValidationError('O resgate anterior não corresponde a um par de caixa simples.')
        debit = debits[0]
        if debit.investment_id != inv.pk and not legacy_link_candidates(credit.connection.user, event, inv).filter(pk=debit.pk).exists():
            raise ValidationError('O registro consolidado não comprova a origem deste resgate.')
        principal = (cost * qty / units).quantize(D('.01'))
        if debit.quantity not in (None, qty) or debit.redemption_principal not in (None, principal):
            raise ValidationError('O custo do resgate anterior diverge do histórico documentado.')
        involved.add(debit.investment_id)
        allowed.add(debit.pk)
        changes.append((debit, {'investment_id': inv.pk, 'quantity': qty, 'redemption_principal': principal}))
        recognized.append({'event': event, 'operation': op, 'date': day, 'gross_gain': gross - principal,
                           'taxes': taxes, 'proof': proof[0]})
        remaining_units -= qty
        remaining_cost -= principal
    if remaining_units <= 0 or remaining_cost <= 0:
        raise ValidationError('Não há principal remanescente para este resgate.')
    before_closing = source.snapshots.filter(reference_at__date__lt=when).order_by('-reference_at', '-id').first()
    if (not before_closing or D(before_closing.facts.get('quantity', -1)) != remaining_units
            or (recognized and before_closing.reference_at <= parse_datetime(recognized[-1]['proof'].facts['date']))):
        raise ValidationError('A última posição anterior ao resgate não confirma a quantidade remanescente.')
    final_event = final_events[0] if final_events else None
    if final_event:
        net = positive(credit.facts.get('amount'))
        gross = positive(final_event.facts.get('amount'))
        expenses = sum((D(v) for v in (final_event.facts.get('expenses') or {}).values() if v is not None), D(0))
        if (final_event.state != 'new' or final_event.revision != 1 or operation_for(final_event)
                or positive(final_event.facts.get('netAmount')) != net
                or positive(final_event.facts.get('quantity')) != remaining_units or gross < net
                or gross - net != expenses or final_event.facts.get('priceFactor') not in (None, 1, '1')):
            raise ValidationError('O evento do resgate final diverge da quantidade ou da liquidação bancária.')
    # Check that no unaccounted financial movement has already sold this holding.
    if inv.transactions.exclude(type='atualizacao').exclude(pk__in=allowed).exists():
        raise ValidationError('Há outros lançamentos na origem que precisam ser conciliados primeiro.')
    stale = []
    for old in recognized:
        liquidation_at = parse_datetime(old['proof'].facts.get('date', ''))
        for snapshot in source.snapshots.select_related('movement'):
            if (liquidation_at and snapshot.reference_at < liquidation_at
                    and snapshot.movement.date >= old['date'] and D(snapshot.facts.get('quantity', 0)) > remaining_units):
                stale.append(snapshot)
                changes.append((snapshot.movement, {'affects_value': False, 'quantity': None}))
    for m in inv.transactions.filter(type='atualizacao', pluggy_snapshot__isnull=True):
        if (baseline and m.date == baseline.date and any(m.current_value == D(s.facts['balance']) for s in stale)):
            changes.append((m, {'affects_value': False, 'quantity': None}))
        elif m.affects_value:
            raise ValidationError('Há uma avaliação manual de origem que exige conferência.')
    closing = source.snapshots.order_by('-reference_at', '-id').first()
    if not closing or closing.reference_at.date() != when or D(closing.facts['balance']) != 0:
        raise ValidationError('Falta a posição oficial após o resgate total.')
    return {'source': source, 'buy': buy, 'opening_operation': buy_op, 'changes': changes,
            'recognized': recognized, 'principal': remaining_cost, 'quantity': remaining_units,
            'final_event': final_event,
            'involved': involved, 'closing': closing,
            'proofs': [{'event_id': e.pk, 'revision': e.revision} for e in events]}


def purchase_options(debit):
    if ('criptomoedas' not in str(debit.facts.get('description', '')).lower()
            or debit.facts.get('type') != 'DEBIT' or hasattr(debit, 'investment_purchase')):
        return []
    try:
        net = receipt(debit, 'DEBIT')
    except ValidationError:
        return []
    credits = []
    for c in InvestmentCashEvidence.objects.filter(connection=debit.connection, account_id=debit.account_id,
            facts__type='CREDIT', facts__status='POSTED', facts__currencyCode='BRL',
            funded_purchase__isnull=True):
        if (D(c.facts.get('amount', 0)) == net and event_date(c.facts) == event_date(debit.facts)
                and parse_datetime(c.facts['date']) <= parse_datetime(debit.facts['date'])
                and str(c.facts.get('description', '')).lower().startswith('resgate - ')):
            credits.append(c)
    if len(credits) != 1:
        return []
    credit = credits[0]
    try:
        registered = registered_source_plan(credit)
        receipt(credit, 'CREDIT', registered=bool(registered))
    except ValidationError:
        return []
    if registered:
        return [{'source_id': registered['source'].pk, 'credit_id': credit.pk,
                 'description': registered['source'].investment.description,
                 'principal': str(registered['principal']), 'net_gain': str(net - registered['principal']),
                 'date': event_date(debit.facts).isoformat(), 'amount': str(net)}]
    from bank_sync.auto_reconciliation import family
    closed = []
    for source in ExternalInvestment.objects.filter(connection=debit.connection, facts__status='TOTAL_WITHDRAWAL'):
        reference = source.reference_at or parse_datetime(source.facts.get('date') or '')
        if (reference and reference.date() == event_date(credit.facts)
                and family(source.facts.get('name')).intersection(family(credit.facts.get('description')))):
            closed.append(source.pk)
    if len(closed) != 1:
        return []
    choices = []
    for source in ExternalInvestment.objects.filter(connection=debit.connection,
            investment__user=debit.connection.user, facts__status='TOTAL_WITHDRAWAL').select_related('investment__asset', 'investment__broker'):
        try:
            plan = source_plan(source, credit)
        except (ValidationError, InvalidOperation):
            continue
        choices.append({'source_id': source.pk, 'credit_id': credit.pk, 'description': source.investment.description,
                        'principal': str(plan['principal']), 'net_gain': str(net - plan['principal']),
                        'date': event_date(debit.facts).isoformat(), 'amount': str(net)})
    return choices


def journal_row(movement):
    return {'id': movement.pk, 'investment_id': movement.investment_id, 'date': movement.date,
            'amount': movement.amount, 'quantity': movement.quantity,
            'redemption_principal': movement.redemption_principal, 'affects_value': movement.affects_value,
            'notes': movement.notes}


@investment_atomic()
def register_purchase(user, debit_id, revision, source_id, credit_id, symbol, quantity, evidence=''):
    Service.lock_user(user)
    debit = InvestmentCashEvidence.objects.select_for_update().get(pk=debit_id, connection__user=user)
    connection = BankConnection.objects.select_for_update().get(pk=debit.connection_id)
    complete(connection)
    quantity = positive(quantity)
    if quantity.as_tuple().exponent < -8 or quantity >= D('1000000000000'):
        raise ValidationError('Informe a quantidade com até oito casas decimais.')
    if not isinstance(symbol, str):
        raise ValidationError('Informe o símbolo da criptomoeda.')
    symbol = symbol.strip().upper()
    if not re.fullmatch('[A-Z0-9]{2,12}', symbol):
        raise ValidationError('Informe o símbolo da criptomoeda, por exemplo BTC.')
    if debit.revision != revision:
        raise ValidationError('O comprovante mudou; confira os novos dados.')
    existing = InvestmentBankTrade.objects.filter(debit=debit).first()
    if existing:
        if (existing.quantity != quantity or existing.investment.asset.symbol != symbol
                or existing.debit_revision != debit.revision or existing.credit_revision != existing.credit.revision
                or existing.state != 'applied'):
            raise ValidationError('A compra já foi registrada com outros dados; revise a operação existente.')
        return existing
    options = purchase_options(debit)
    if not any(c['source_id'] == source_id and c['credit_id'] == credit_id for c in options):
        raise ValidationError('Não há um resgate documentado e inequívoco para financiar esta compra.')
    credit = InvestmentCashEvidence.objects.select_for_update().get(pk=credit_id, connection=connection)
    net = receipt(debit, 'DEBIT')
    registered = registered_source_plan(credit)
    if receipt(credit, 'CREDIT', registered=bool(registered)) != net:
        raise ValidationError('O valor do resgate diverge da compra.')
    source = ExternalInvestment.objects.select_for_update().get(pk=source_id, connection=connection, investment__user=user)
    plan = registered or source_plan(source, credit)
    if plan['source'].pk != source.pk:
        raise ValidationError('O resgate registrado pertence a outro título.')
    wallet = Service.get_or_create_default_wallet(user)
    assets = list(Asset.objects.filter(user=user, asset_type='crypto', currency='BRL', symbol=symbol))
    if len(assets) > 1:
        raise ValidationError('Há mais de um cadastro da mesma criptomoeda; unifique a identificação primeiro.')
    name = 'Bitcoin' if symbol == 'BTC' else symbol
    if assets:
        asset = assets[0]
    else:
        description = name
        if Asset.objects.filter(user=user, description=name, symbol=symbol).exists():
            description += ' (BRL)'
        asset = Asset(user=user, symbol=symbol, asset_type='crypto', currency='BRL', description=description)
        asset.full_clean()
        asset.save()
    holdings = list(Investment.objects.filter(user=user, asset=asset, broker=source.investment.broker))
    if len(holdings) > 1:
        raise ValidationError('Há mais de uma posição dessa criptomoeda no mesmo banco.')
    if not holdings:
        from investments.services.products import ensure_unclassified_opening_is_not_already_assessed
        ensure_unclassified_opening_is_not_already_assessed(user, source.investment.broker, 'crypto', event_date(debit.facts))
    target = holdings[0] if holdings else Investment.objects.create(user=user, asset=asset, broker=source.investment.broker,
        description=f'{name} ({source.investment.broker.description})', start_date=event_date(debit.facts),
        notes='Compra registrada pelo extrato. Valor inicial pelo custo pago; a instituição não forneceu cotação atual.')
    if target.transactions.filter(type='aporte', date=event_date(debit.facts), amount=net).exists():
        raise ValidationError('Há uma compra semelhante já registrada. Vincule-a antes de criar outra.')
    affected = set(plan['involved']) | {wallet.pk, target.pk}
    before = Service.snapshot_balances(user, affected)
    values_before = {p['investment'].pk: p['value'] for p in InvestmentService.get_positions(user)}
    wallet_before = values_before[wallet.pk]
    journal = {'changes': [], 'source_events': plan['proofs'], 'new_movements': [], 'operations': [],
               'user_confirmation': {'symbol': symbol, 'quantity': str(quantity), 'evidence': evidence},
               'credit_facts': credit.facts, 'debit_facts': debit.facts,
               'source_closed': not bool(registered)}
    if not registered:
        journal['source_snapshot'] = {'id': plan['closing'].pk, 'facts': plan['closing'].facts,
                                      'reference_at': plan['closing'].reference_at}
    for movement, updates in plan['changes']:
        original = journal_row(movement)
        for key, value in updates.items():
            setattr(movement, key, value)
        movement.notes += '\nReconstrução documentada de resgate e reinvestimento pelo extrato.'
        movement.full_clean()
        movement.save()
        journal['changes'].append({'before': original, 'after': journal_row(movement)})
    def add(investment, kind, value=0, day=None, **kwargs):
        m = Movement(user=user, investment=investment, date=day or event_date(debit.facts), type=kind,
                     amount=value, notes='Integração: resgate e compra de criptomoeda documentados no extrato.', **kwargs)
        m.full_clean()
        m.save()
        journal['new_movements'].append(m.pk)
        return m
    for old in plan['recognized']:
        made = []
        gain = old['gross_gain']
        if gain:
            made.append(add(source.investment, 'rendimento' if gain > 0 else 'custo', abs(gain), day=old['date']))
        if old['taxes']:
            made.append(add(source.investment, 'custo', old['taxes'], day=old['date']))
        op = old['operation']
        journal['operations'].append({'id': op.pk, 'evidence': op.evidence, 'state': op.state,
                                      'movement_ids': list(op.movements.values_list('pk', flat=True))})
        op.movements.add(*made)
        op.evidence += '\nCusto e despesas reconstituídos pela quantidade da aquisição e comprovantes bancários.'
        op.state = 'applied'
        op.save(update_fields=['state', 'evidence'])
        old['event'].state = 'applied'
        old['event'].save(update_fields=['state'])
    op = plan['opening_operation']
    if op:
        journal['operations'].append({'id': op.pk, 'evidence': op.evidence, 'state': op.state,
                                      'movement_ids': list(op.movements.values_list('pk', flat=True))})
        op.evidence += '\nData da aquisição conferida com o débito bancário e o evento de compra.'
        op.save(update_fields=['evidence'])
    sale_uuid, purchase_uuid = uuid4(), uuid4()
    source_rows = []
    profit = net - plan['principal']
    if registered:
        funding = plan['funding']
    else:
        final_event = plan['final_event']
        gross_gain = D(final_event.facts['amount']) - plan['principal'] if final_event else profit
        if gross_gain:
            source_rows.append(add(source.investment, 'rendimento' if gross_gain > 0 else 'custo', abs(gross_gain), operation_id=sale_uuid))
        if final_event and D(final_event.facts['amount']) > net:
            source_rows.append(add(source.investment, 'custo', D(final_event.facts['amount']) - net, operation_id=sale_uuid))
        source_rows.append(add(source.investment, 'resgate', net, quantity=plan['quantity'],
                               redemption_principal=plan['principal'], operation_id=sale_uuid))
        funding = add(wallet, 'aporte', net, operation_id=sale_uuid)
        source_rows.append(funding)
    target_rows = [add(wallet, 'resgate', net, operation_id=purchase_uuid),
                   add(target, 'aporte', net, quantity=quantity, operation_id=purchase_uuid, funding_transaction=funding)]
    if not registered:
        source_rows.append(add(source.investment, 'atualizacao', current_value=0, quantity=0))
        if plan['final_event']:
            op = ReconciledInvestmentOperation.objects.create(event=plan['final_event'], kind='sell', state='applied',
                automatic=True, evidence='Resgate final registrado junto à compra, com liquidação e custo reconstituídos.')
            op.movements.set(source_rows)
            op.cash_evidence.add(credit)
            plan['final_event'].state = 'applied'
            plan['final_event'].save(update_fields=['state'])
    target.status = 'active'
    target.save(update_fields=['status'])
    Service.validate_balances(user, affected, before)
    values_after = {p['investment'].pk: p['value'] for p in InvestmentService.get_positions(user)}
    if values_after[wallet.pk] != wallet_before - (net if registered else 0):
        raise ValidationError('A operação não preservou o saldo do caixa.')
    for pk, value in values_before.items():
        if pk not in (target.pk, wallet.pk) and values_after[pk] != value:
            raise ValidationError('A operação alteraria outra posição já conciliada.')
    position = InvestmentService.get_position(source.investment)
    if not registered and (position['remaining_principal'] != 0 or position['quantity'] != 0 or position['value'] != 0):
        raise ValidationError('O custo e a quantidade da origem não fecharam após o resgate total.')
    journal = json.loads(json.dumps(journal, cls=DjangoJSONEncoder))
    trade = InvestmentBankTrade.objects.create(credit=credit, debit=debit, credit_revision=credit.revision,
        debit_revision=debit.revision, source=source, investment=target, quantity=quantity, amount=net,
        evidence='Dados do extrato e histórico da instituição; criptomoeda e quantidade confirmadas pelo usuário. ' + str(evidence),
        journal=journal)
    for cash, movements in [(credit, source_rows), (debit, target_rows)]:
        if registered and cash.pk == credit.pk:
            continue
        review = InvestmentCashReview.objects.create(cash=cash, revision=cash.revision, action='apply', automatic=True,
                                                    trade=trade, evidence=trade.evidence)
        review.movements.set(movements)
    return trade


def flag_bank_trade_conflicts(connection):
    changed_any = False
    for trade in InvestmentBankTrade.objects.filter(debit__connection=connection, state='applied').select_related('credit', 'debit', 'source'):
        proofs = trade.journal.get('accepted_proofs') or {'source_events': trade.journal.get('source_events', [])}
        changed = (trade.credit.revision != trade.credit_revision or trade.debit.revision != trade.debit_revision)
        for proof in proofs['source_events']:
            if not InvestmentEvent.objects.filter(pk=proof['event_id'], revision=proof['revision']).exists():
                changed = True
        if proofs.get('source_state'):
            if (trade.source.facts.get('status') != proofs['source_state']['status']
                    or any(D(trade.source.facts.get(k, -1)) != D(proofs['source_state'][k]) for k in ['balance', 'quantity'])):
                changed = True
        elif trade.journal.get('source_closed') and (trade.source.facts.get('status') != 'TOTAL_WITHDRAWAL'
                or D(trade.source.facts.get('balance', -1)) != 0 or D(trade.source.facts.get('quantity', -1)) != 0):
            changed = True
        if changed:
            trade.state = 'conflict'
            trade.save(update_fields=['state'])
            changed_any = True
    if changed_any:
        from investments.events import mark_changed
        mark_changed(connection.user_id)


@investment_atomic()
def keep_bank_trade(user, cash_id, revision, evidence):
    from django.db.models import Q
    Service.lock_user(user)
    cash = InvestmentCashEvidence.objects.select_for_update().get(pk=cash_id, connection__user=user)
    if cash.revision != revision or not isinstance(evidence, str) or not evidence.strip():
        raise ValidationError('Confira a versão atual e informe por que deseja manter os registros.')
    trade = InvestmentBankTrade.objects.select_for_update().get(Q(credit=cash) | Q(debit=cash), state='conflict')
    complete(cash.connection)
    accepted = {'source_events': list(InvestmentEvent.objects.filter(
        pk__in=[p['event_id'] for p in trade.journal['source_events']]).values('pk', 'revision'))}
    accepted['source_events'] = [{'event_id': p['pk'], 'revision': p['revision']} for p in accepted['source_events']]
    accepted['source_state'] = {k: str(trade.source.facts.get(k)) for k in ['status', 'balance', 'quantity']}
    trade.journal.setdefault('decisions', []).append({'at': timezone.now().isoformat(), 'evidence': evidence,
        'credit_revision': trade.credit.revision, 'debit_revision': trade.debit.revision})
    trade.journal['accepted_proofs'] = accepted
    for receipt_row in [trade.credit, trade.debit]:
        if not receipt_row.reviews.filter(revision=receipt_row.revision).exists():
            old = receipt_row.reviews.filter(trade=trade).order_by('-revision').first()
            if old:
                review = InvestmentCashReview.objects.create(cash=receipt_row, revision=receipt_row.revision,
                    action='apply', trade=trade, evidence='Registros mantidos após alteração da fonte: ' + evidence)
                review.movements.set(old.movements.all())
    trade.credit_revision, trade.debit_revision = trade.credit.revision, trade.debit.revision
    trade.state = 'applied'
    trade.save(update_fields=['state', 'journal', 'credit_revision', 'debit_revision'])
    from investments.events import mark_changed
    mark_changed(user.pk)
    return trade
