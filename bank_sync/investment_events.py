"""Staged investment events and explicit, atomic reconciliation."""
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from bank_sync.models import (
    BankConnection,
    ExternalInvestment,
    InvestmentEvent,
    InvestmentEventRevision,
    ReconciledInvestmentOperation,
    CashAllocation,
    InvestmentReconciliationBaseline,
    InvestmentHistoryJob,
    InvestmentCashEvidence,
)
from bank_sync.services import configured_reader
from bank_sync.investments import ready
from clients.pluggy.reader import ProbeError
from investments.events import investment_atomic
from investments.models import InvestmentTransaction as Movement
from investments.services.investment import InvestmentService
from investments.services.transaction import (
    InvestmentTransactionService as Service,
)

D = lambda x: Decimal(str(x))
FIELDS = (
    'date',
    'tradeDate',
    'type',
    'movementType',
    'description',
    'quantity',
    'value',
    'amount',
    'netAmount',
    'expenses',
    'brokerageNumber',
    'priceFactor',
)


def event_date(facts):
    raw = facts.get('tradeDate') or facts.get('date')
    parsed = parse_datetime(raw or '')
    if parsed is None:
        raise ValidationError('Data de liquidação ausente ou inválida.')
    return parsed.date()


def classify(facts):
    kind = facts.get('type')
    if kind == 'SELL' and not facts.get('quantity') and 'rendimento' in str(facts.get('description') or '').lower():
        return (
            'ambiguous',
            'SELL descrito como rendimento sem quantidade: exige evidência adicional.',
        )
    return {
        'BUY': 'buy',
        'SELL': 'sell',
        'INTEREST': 'income',
        'TAX': 'tax',
        'TRANSFER': 'transfer',
        'AMORTIZATION': 'amortization',
    }.get(kind, 'ambiguous'), ''


def operation_for(event):
    membership = getattr(event, 'operation_membership', None)
    return membership.operation if membership else getattr(event, 'operation', None)


def flag_conflict(operation, reason):
    operation.state = 'conflict'
    operation.save(update_fields=['state'])
    ids = list(operation.event_memberships.values_list('event_id', flat=True))
    InvestmentEvent.objects.filter(pk__in=[operation.event_id, *ids]).update(state='conflict', reason=reason)


def collect(job, reader=None, lease_token=None):
    def heartbeat():
        now = timezone.now()
        until = now + timedelta(minutes=10)
        if lease_token:
            updated = BankConnection.objects.filter(
                pk=job.connection_id,
                lease_token=lease_token,
                lease_until__gt=now,
            ).update(lease_until=until)
            if not updated:
                raise ProbeError('A execução perdeu a reserva da conexão; solicite uma nova coleta.')
        job.lease_until = until
        job.save(update_fields=['progress', 'lease_until'])

    reader = reader or configured_reader()
    reader.authenticate()
    path = '/items/' + str(job.connection.item_id)
    start = reader.request(path)
    ready(start)
    sources = list(ExternalInvestment.objects.filter(connection=job.connection))
    total = 0
    for i, source in enumerate(sources):
        rows = reader.numbered(
            '/investments/' + str(source.external_id) + '/transactions',
            {'pageSize': 500},
        )
        heartbeat()
        with transaction.atomic():
            for row in rows:
                facts = {key: row.get(key) for key in FIELDS}
                event_date(facts)
                (event, created,) = InvestmentEvent.objects.select_for_update().get_or_create(
                    connection=job.connection,
                    external_id=row['id'],
                    defaults={'facts': facts},
                )
                if not created and event.facts != facts:
                    InvestmentEventRevision.objects.get_or_create(
                        event=event,
                        revision=event.revision,
                        defaults={'facts': event.facts},
                    )
                    event.revision += 1
                    event.facts = facts
                    operation = operation_for(event)
                    event.state = 'conflict' if operation or event.state == 'ignored' else 'new'
                    if operation:
                        flag_conflict(
                            operation,
                            'Movimentação revisada pela fonte; revise a operação completa.',
                        )
                        event.reason = 'Movimentação revisada pela fonte; revise a operação completa.'
                event.investments.add(source)
                kind, reason = classify(facts)
                if event.state != 'conflict':
                    event.reason = reason
                if not operation_for(event) and event.state != 'conflict' and source.investment_id:
                    baseline = getattr(source.investment, 'reconciliation_baseline', None)
                    if baseline and event_date(facts) <= baseline.date:
                        event.state = 'historical'
                        event.reason = (
                            'Anterior à data-base; vincular ao existente ou reconstruir a sequência completa.'
                        )
                event.last_seen_job = job
                event.save()
                total += 1
            job.progress = {
                'titles': i + 1,
                'total_titles': len(sources),
                'events': total,
            }
            heartbeat()
    accounts = reader.numbered('/accounts', {'itemId': str(job.connection.item_id)})
    for account in accounts:
        if account.get('type') == 'CREDIT':
            continue
        cash_rows = reader.transactions(account['id'])
        heartbeat()
        with transaction.atomic():
            for row in cash_rows:
                facts = {
                    k: row.get(k)
                    for k in (
                        'date',
                        'amount',
                        'type',
                        'description',
                        'currencyCode',
                        'status',
                    )
                }
                (cash, created,) = InvestmentCashEvidence.objects.select_for_update().get_or_create(
                    connection=job.connection,
                    external_id=row['id'],
                    defaults={'account_id': account['id'], 'facts': facts},
                )
                if not created and cash.facts != facts:
                    cash.history.append({'revision': cash.revision, 'facts': cash.facts})
                    cash.revision += 1
                    cash.facts = facts
                    cash.save()
                    for operation in cash.operations.all():
                        flag_conflict(
                            operation,
                            'Liquidação bancária revisada pela fonte.',
                        )
    end = reader.request(path)
    ready(end)
    if end.get('lastUpdatedAt') != start.get('lastUpdatedAt'):
        raise ProbeError('A conexão mudou durante a coleta. Eventos coletados aguardam nova coleta completa.')
    heartbeat()
    return total


@investment_atomic()
def reconcile(
    user,
    pk,
    revision,
    action,
    *,
    movement_ids=(),
    funding_ids=(),
    principal=None,
    evidence='',
    expected_kind=None,
    allocations=(),
    cash_ids=()
):
    Service.lock_user(user)
    event = InvestmentEvent.objects.select_for_update().get(pk=pk, connection__user=user)
    if event.revision != revision:
        raise ValidationError('O evento mudou; revise a versão atual.')
    if action == 'keep':
        if event.state != 'conflict' or not evidence.strip():
            raise ValidationError('Informe o motivo para manter a operação após revisar o conflito.')
        op = operation_for(event)
        if op:
            op.state = 'linked'
            op.evidence += '\nRevisão mantida sem alterar lançamentos: ' + evidence
            op.save(update_fields=['state', 'evidence'])
            ids = list(op.event_memberships.values_list('event_id', flat=True))
            InvestmentEvent.objects.filter(pk__in=[op.event_id, *ids]).update(state='linked', reason=evidence)
        else:
            event.state = 'ignored'
            event.reason = evidence
            event.save(update_fields=['state', 'reason'])
        return op
    if event.state == 'conflict':
        raise ValidationError('O evento mudou; revise a versão atual.')
    if hasattr(event, 'operation_membership'):
        return event.operation_membership.operation
    if hasattr(event, 'operation'):
        return event.operation
    if not event.last_seen_job_id or event.last_seen_job.state != 'succeeded':
        raise ValidationError('Conclua uma coleta completa antes de conciliar este evento.')
    if action == 'ignore':
        if not evidence.strip():
            raise ValidationError('Informe o motivo.')
        event.state = 'ignored'
        event.reason = evidence
        event.save()
        return None
    sources = list(event.investments.filter(investment__user=user))
    if len(sources) != 1:
        raise ValidationError('Vincule o evento a um título inequívoco antes de aplicar.')
    source = sources[0]
    inv = source.investment
    kind, reason = classify(event.facts)
    if action == 'link':
        ids = list(set(int(x) for x in movement_ids))
        rows = list(Movement.objects.filter(user=user, pk__in=ids))
        if not rows or len(rows) != len(ids) or not any(x.investment_id == inv.pk for x in rows):
            raise ValidationError('Selecione lançamentos próprios da operação e do título.')
        if not evidence.strip():
            raise ValidationError('Descreva a correspondência documental.')
        op = ReconciledInvestmentOperation.objects.create(event=event, kind=kind, state='linked', evidence=evidence)
        op.movements.set(rows)
        event.state = 'linked'
        event.save(update_fields=['state'])
        return op
    if action != 'apply':
        raise ValidationError('Ação inválida.')
    baseline = getattr(inv, 'reconciliation_baseline', None)
    if event.state in ('historical', 'ignored') or (baseline and event_date(event.facts) <= baseline.date):
        raise ValidationError('Evento histórico/ignorado não pode gerar lançamentos isolados.')
    if kind == 'ambiguous':
        if expected_kind not in ('income', 'sell') or not evidence.strip():
            raise ValidationError(reason)
        kind = expected_kind
    if kind == 'transfer':
        raise ValidationError(
            'Este evento exige conciliação composta e evidência de caixa; não será aplicado por estimativa.'
        )
    facts = event.facts
    if facts.get('priceFactor') is not None and D(facts['priceFactor']) != 1:
        raise ValidationError('Fator de preço exige conversão documental antes da aplicação.')
    when = event_date(facts)
    cash = list(InvestmentCashEvidence.objects.select_for_update().filter(connection=event.connection, pk__in=cash_ids))
    if not cash or len(cash) != len(set(cash_ids)):
        raise ValidationError('Selecione as liquidações bancárias próprias para esta operação.')
    if any(c.operations.exclude(state='ignored').exists() for c in cash):
        raise ValidationError('Uma liquidação já foi utilizada; concilie a operação agrupada existente.')
    for c in cash:
        if c.facts.get('currencyCode') != 'BRL' or c.facts.get('status') != 'POSTED':
            raise ValidationError('Liquidação pendente ou em outra moeda.')
        if abs((event_date(c.facts) - when).days) > 7:
            raise ValidationError('Liquidação fora da janela de conciliação; revise as datas.')
    if inv.asset.currency != 'BRL':
        raise ValidationError('Conciliação automática disponível apenas em BRL.')
    raw = facts.get('netAmount')
    if raw is None:
        raise ValidationError('Valor líquido não informado; confirme a liquidação antes de aplicar.')
    net = Service.positive_amount(raw)
    if facts.get('amount') is None:
        raise ValidationError('Valor bruto ausente; não é possível determinar custos e resultado.')
    gross = Service.positive_amount(facts['amount'])
    if not evidence.strip():
        raise ValidationError('Informe a evidência de liquidação na conta.')
    wallet = Service.get_or_create_default_wallet(user)
    expected_direction = 'DEBIT' if kind in ('buy', 'tax') else 'CREDIT'
    if (
        any(c.facts.get('type') != expected_direction for c in cash)
        or sum(abs(D(c.facts['amount'])) for c in cash) != net
    ):
        raise ValidationError('Valor ou direção da liquidação diverge do evento.')
    before = Service.snapshot_balances(user, [wallet.pk, inv.pk])
    op = ReconciledInvestmentOperation.objects.create(event=event, kind=kind, state='applied', evidence=evidence)
    op.cash_evidence.set(cash)
    made = []

    def add(target, t, amount=0, **kw):
        m = Movement(
            user=user,
            investment=target,
            date=when,
            type=t,
            amount=D(amount),
            notes='Evento Pluggy ' + event.external_id + '; ' + evidence,
            **kw
        )
        m.full_clean()
        m.save()
        made.append(m)
        return m

    if kind == 'income':
        if gross < net:
            raise ValidationError('Valor bruto menor que o líquido.')
        add(inv, 'rendimento', gross, affects_value=False)
        if gross > net:
            add(inv, 'custo', gross - net, affects_value=False)
        add(wallet, 'aporte', net)
    elif kind == 'buy':
        quantity = (
            Service.positive_amount(facts['quantity'])
            if facts.get('quantity') is not None and D(facts['quantity']).as_tuple().exponent >= -2
            else D(facts.get('quantity') or 0)
        )
        if quantity <= 0:
            raise ValidationError('Quantidade de compra ausente.')
        if net < gross:
            raise ValidationError('Débito da compra menor que o valor bruto.')
        if net != gross and not facts.get('expenses'):
            raise ValidationError('Despesas da compra precisam ser comprovadas.')
        debit = add(wallet, 'resgate', net)
        add(
            inv,
            'aporte',
            gross,
            quantity=quantity,
            unit_price=D(facts['value']) if facts.get('value') else None,
        )
        if net > gross:
            add(inv, 'custo', net - gross, affects_value=False)
        allocate_cash(user, wallet, debit, when, allocations)
    elif kind == 'tax':
        add(inv, 'custo', net, affects_value=False)
        debit = add(wallet, 'resgate', net)
        allocate_cash(user, wallet, debit, when, allocations)
    elif kind == 'amortization':
        position = InvestmentService.get_position(inv, as_of=when)
        if gross < net or gross > position['remaining_principal']:
            raise ValidationError('Amortização excede o principal conhecido.')
        add(inv, 'resgate', net, redemption_principal=gross)
        if gross > net:
            add(inv, 'custo', gross - net, affects_value=False)
        add(wallet, 'aporte', net)
    elif kind == 'sell':
        if principal is None:
            raise ValidationError('Principal/custo da parcela vendida não comprovado.')
        cost = Service.positive_amount(principal)
        units = D(facts.get('quantity') or 0)
        if units <= 0 or gross < net:
            raise ValidationError('Quantidade ou valores da venda inválidos.')
        quote_ids = list(
            inv.transactions.filter(pluggy_snapshot__reference_at__date__gte=when).values_list('pk', flat=True)
        )
        position = InvestmentService.get_position(inv, as_of=when, exclude_ids=quote_ids)
        if units > position['quantity'] or cost > position['remaining_principal']:
            raise ValidationError('Quantidade vendida excede a posição conhecida.')
        # Explicit cost and execution proceeds recognize realization once; quote corrections remain valuations.
        pnl = gross - cost
        if pnl:
            add(
                inv,
                'rendimento' if pnl > 0 else 'custo',
                abs(pnl),
                affects_value=False,
            )
        if gross > net:
            add(inv, 'custo', gross - net, affects_value=False)
        allocated = (position['value'] * units / position['quantity']).quantize(D('0.01'))
        add(
            inv,
            'atualizacao',
            current_value=position['value'] - allocated + net,
        )
        add(inv, 'resgate', net, quantity=units, redemption_principal=cost)
        add(wallet, 'aporte', net)
    else:
        raise ValidationError('Classificação sem aplicação financeira definida.')
    # A quote already containing this event remains authoritative, even when history arrives later.
    latest = source.snapshots.order_by('-reference_at', '-id').first()
    if latest and latest.reference_at.date() >= when:
        saved = latest.facts
        m = Movement(
            user=user,
            investment=inv,
            date=max(when, latest.movement.date),
            type='atualizacao',
            amount=0,
            current_value=D(saved['balance']),
            quantity=D(saved['quantity']),
            notes='Preservação da posição oficial após conciliação de evento.',
        )
        m.full_clean()
        m.save()
        made.append(m)
    Service.validate_balances(user, [wallet.pk, inv.pk], before)
    op.movements.set(made)
    event.state = 'applied'
    event.save(update_fields=['state'])
    return op


def allocate_cash(user, wallet, debit, when, allocations):
    """Lock and reserve explicit funding for a cash debit within the caller's transaction."""
    if not allocations or len({int(a['credit_id']) for a in allocations}) != len(allocations):
        raise ValidationError('Informe créditos distintos que financiam o débito.')
    total = D(0)
    for allocation in allocations:
        credit = Movement.objects.select_for_update().get(
            pk=allocation['credit_id'],
            user=user,
            investment=wallet,
            type__in=['aporte', 'rendimento'],
        )
        amount = Service.positive_amount(allocation['amount'])
        used = credit.cash_allocations_out.aggregate(v=Sum('amount'))['v'] or D(0)
        used += sum((m.amount for m in credit.funded_transactions.all()), D(0))
        if credit.date > when or amount > credit.amount - used:
            raise ValidationError('Crédito insuficiente ou posterior ao débito.')
        CashAllocation.objects.create(credit=credit, debit=debit, amount=amount)
        total += amount
    if total != debit.amount:
        raise ValidationError('As parcelas devem fechar exatamente o débito.')


@investment_atomic()
def reconcile_purchase_group(user, events, cash_ids, allocations, shared_cost, evidence):
    Service.lock_user(user)
    selected = []
    for selected_event in events:
        event = InvestmentEvent.objects.select_for_update().get(pk=selected_event['id'], connection__user=user)
        if event.revision != selected_event['revision'] or event.state not in ('new',):
            raise ValidationError('Grupo contém evento histórico, alterado ou já processado.')
        if not event.last_seen_job_id or event.last_seen_job.state != 'succeeded':
            raise ValidationError('Coleta incompleta.')
        sources = list(event.investments.filter(investment__user=user))
        if len(sources) != 1 or classify(event.facts)[0] != 'buy':
            raise ValidationError('Agrupamento automático disponível para compras inequívocas.')
        if hasattr(event, 'operation') or hasattr(event, 'operation_membership'):
            raise ValidationError('Evento já utilizado.')
        selected.append((event, sources[0]))
    if len(selected) < 2 or len({e.pk for e, s in selected}) != len(selected):
        raise ValidationError('Selecione pelo menos duas compras distintas.')
    connection = selected[0][0].connection
    if any(e.connection_id != connection.pk for e, s in selected):
        raise ValidationError('Conexões diferentes.')
    dates = {event_date(e.facts) for e, s in selected}
    if len(dates) != 1:
        raise ValidationError('Agrupe compras da mesma data de liquidação.')
    when = dates.pop()
    cash = list(InvestmentCashEvidence.objects.select_for_update().filter(connection=connection, pk__in=cash_ids))
    if not cash or len(cash) != len(set(cash_ids)) or any(c.operations.exists() for c in cash):
        raise ValidationError('Liquidação ausente ou já conciliada.')
    if any(
        c.facts.get('type') != 'DEBIT'
        or c.facts.get('status') != 'POSTED'
        or c.facts.get('currencyCode') != 'BRL'
        or abs((event_date(c.facts) - when).days) > 7
        for c in cash
    ):
        raise ValidationError('Liquidação incompatível.')
    fee = D(shared_cost or 0)
    if not fee.is_finite() or fee < 0 or fee.as_tuple().exponent < -2 or not evidence.strip():
        raise ValidationError('Informe custo comprovado e evidência da nota.')
    gross_total = sum(Service.positive_amount(e.facts['netAmount']) for e, s in selected)
    total = sum(abs(D(c.facts['amount'])) for c in cash)
    if gross_total + fee != total:
        raise ValidationError('Compras e custo compartilhado não fecham o débito bancário.')
    wallet = Service.get_or_create_default_wallet(user)
    before = Service.snapshot_balances(user, [s.investment_id for e, s in selected] + [wallet.pk])
    op = ReconciledInvestmentOperation.objects.create(
        event=selected[0][0],
        kind='purchase_group',
        state='applied',
        evidence=evidence,
    )
    op.cash_evidence.set(cash)
    made = []

    def add(inv, t, amount, **kw):
        m = Movement(user=user, investment=inv, date=when, type=t, amount=D(amount), notes=evidence, **kw)
        m.full_clean()
        m.save()
        made.append(m)
        return m

    debit = add(wallet, 'resgate', total)
    allocate_cash(user, wallet, debit, when, allocations)
    from bank_sync.models import InvestmentOperationEvent

    for event, source in selected:
        f = event.facts
        if (
            source.investment.asset.currency != 'BRL'
            or (f.get('priceFactor') is not None and D(f['priceFactor']) != 1)
            or f.get('quantity') is None
            or D(f['quantity']) <= 0
        ):
            raise ValidationError('Quantidade/moeda inválida.')
        gross = Service.positive_amount(f['amount'])
        net = Service.positive_amount(f['netAmount'])
        if net < gross or (net != gross and not f.get('expenses')):
            raise ValidationError('Custos individuais não comprovados.')
        add(
            source.investment,
            'aporte',
            gross,
            quantity=D(f['quantity']),
            unit_price=D(f['value']) if f.get('value') else None,
        )
        if net > gross:
            add(source.investment, 'custo', net - gross, affects_value=False)
        InvestmentOperationEvent.objects.create(event=event, operation=op)
        event.state = 'applied'
        event.save(update_fields=['state'])
        latest = source.snapshots.order_by('-reference_at', '-id').first()
        if latest and latest.reference_at.date() >= when:
            m = Movement(
                user=user,
                investment=source.investment,
                date=max(when, latest.movement.date),
                type='atualizacao',
                amount=0,
                current_value=D(latest.facts['balance']),
                quantity=D(latest.facts['quantity']),
                notes='Posição oficial preservada após conciliação agrupada.',
            )
            m.full_clean()
            m.save()
            made.append(m)
    if fee:
        add(wallet, 'custo', fee, affects_value=False)
    Service.validate_balances(user, [s.investment_id for e, s in selected] + [wallet.pk], before)
    op.movements.set(made)
    return op


@investment_atomic()
def reconcile_transfer_group(user, selections, principal, evidence):
    from bank_sync.models import InvestmentOperationEvent

    Service.lock_user(user)
    if len(selections) != 2 or not evidence.strip():
        raise ValidationError('Selecione as duas pernas e informe a evidência da transferência.')
    members = []
    for selection in selections:
        e = InvestmentEvent.objects.select_for_update().get(pk=selection['id'], connection__user=user)
        if (
            e.revision != selection['revision']
            or e.state != 'new'
            or e.facts.get('type') != 'TRANSFER'
            or not e.last_seen_job_id
            or e.last_seen_job.state != 'succeeded'
        ):
            raise ValidationError('Evento de transferência não disponível.')
        sources = list(e.investments.filter(investment__user=user))
        if len(sources) != 1:
            raise ValidationError('Título da transferência ambíguo.')
        members.append((e, sources[0]))
    debits = [x for x in members if x[0].facts.get('movementType') == 'DEBIT']
    credits = [x for x in members if x[0].facts.get('movementType') == 'CREDIT']
    if len(debits) != 1 or len(credits) != 1:
        raise ValidationError('Direções da transferência não comprovadas.')
    debit, source = debits[0]
    credit, target = credits[0]
    if (
        source.investment_id == target.investment_id
        or source.connection_id != target.connection_id
        or source.investment.asset.currency != 'BRL'
        or source.investment.asset.currency != target.investment.asset.currency
        or source.investment.asset_id != target.investment.asset_id
    ):
        raise ValidationError('Origem/destino inválidos ou transferência cambial sem cotação.')
    when = event_date(debit.facts)
    if event_date(credit.facts) != when:
        raise ValidationError('Datas das pernas divergentes.')
    units = D(debit.facts.get('quantity') or 0)
    if units <= 0 or units != D(credit.facts.get('quantity') or 0):
        raise ValidationError('Quantidades da transferência não comprovadas.')
    cost = Service.positive_amount(principal)
    inv = source.investment
    dest = target.investment
    position = InvestmentService.get_position(
        inv,
        as_of=when,
        exclude_ids=list(
            inv.transactions.filter(pluggy_snapshot__reference_at__date__gte=when).values_list('id', flat=True)
        ),
    )
    if units > position['quantity'] or cost > position['remaining_principal']:
        raise ValidationError('Quantidade/custo excede a posição conhecida.')
    before = Service.snapshot_balances(user, [inv.pk, dest.pk])
    op = ReconciledInvestmentOperation.objects.create(event=debit, kind='transfer', state='applied', evidence=evidence)
    allocated = (position['value'] * units / position['quantity']).quantize(D('0.01'))
    made = []

    def add(investment, t, amount=0, **kw):
        m = Movement(user=user, investment=investment, date=when, type=t, amount=D(amount), notes=evidence, **kw)
        m.full_clean()
        m.save()
        made.append(m)

    add(inv, 'atualizacao', current_value=position['value'] - allocated + cost)
    add(inv, 'resgate', cost, quantity=units, redemption_principal=cost)
    prior = InvestmentService.get_position(dest, as_of=when)['value']
    add(dest, 'aporte', cost, quantity=units)
    add(dest, 'atualizacao', current_value=prior + allocated)
    for event, ext in members:
        InvestmentOperationEvent.objects.create(event=event, operation=op)
        event.state = 'applied'
        event.save(update_fields=['state'])
        latest = ext.snapshots.order_by('-reference_at', '-id').first()
        if latest and latest.reference_at.date() >= when:
            m = Movement(
                user=user,
                investment=ext.investment,
                date=max(when, latest.movement.date),
                type='atualizacao',
                current_value=D(latest.facts['balance']),
                quantity=D(latest.facts['quantity']),
                notes='Posição oficial preservada após transferência conciliada.',
            )
            m.full_clean()
            m.save()
            made.append(m)
    Service.validate_balances(user, [inv.pk, dest.pk], before)
    op.movements.set(made)
    return op
