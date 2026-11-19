from datetime import timedelta
from decimal import Decimal
from math import ceil
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from bank_sync.models import (
    BankConnection,
    InvestmentEvent,
    InvestmentHistoryJob,
    InvestmentCashEvidence,
    InvestmentOperationEvent,
    ReconciledInvestmentOperation,
)
from bank_sync.views import api_errors, body
from bank_sync.cash_reviews import bank_rows as cash_rows, candidates as cash_movements, review_cash
from bank_sync.investment_events import reconcile, classify, event_date, operation_for, legacy_link_candidates
from investments.models import InvestmentTransaction


@login_required
def event_page(request):
    return render(request, 'bank_sync/investment_events.html')


@login_required
@require_GET
@api_errors
def event_list(request):
    pending_states = ('new', 'historical', 'conflict')
    resolved_states = ('applied', 'linked', 'ignored')
    all_rows = InvestmentEvent.objects.filter(connection__user=request.user)
    # Bank statements can arrive before (or without) an investment event.
    # Expose them independently; a bank description alone cannot establish an
    # asset, quantity, cost basis or a safe new financial movement.
    bank_rows = cash_rows(request.user)
    counts = dict(all_rows.values('state').annotate(total=Count('id')).values_list('state', 'total'))
    summary = {
        'pending': sum(counts.get(s, 0) for s in pending_states),
        'resolved': sum(counts.get(s, 0) for s in resolved_states),
        'total': sum(counts.values()),
        'bank_pending': bank_rows.filter(reviewed=False, prior_to_baseline=False).count(),
        'bank_prior': bank_rows.filter(reviewed=False, prior_to_baseline=True).count(),
    }
    selected_state = request.GET.get('state') or 'pending'
    if selected_state == 'pending':
        rows = all_rows.filter(state__in=pending_states)
    elif selected_state == 'resolved':
        rows = all_rows.filter(state__in=resolved_states)
    elif selected_state == 'all':
        rows = all_rows
    elif selected_state in ('bank', 'bank_history', 'bank_prior'):
        rows = all_rows.none()
    elif selected_state in pending_states + resolved_states:
        rows = all_rows.filter(state=selected_state)
    else:
        raise ValidationError('Situação inválida. Selecione pendências, histórico ou extrato sem vínculo.')
    page_size = 20
    if selected_state in ('bank', 'bank_history', 'bank_prior'):
        bank_rows = bank_rows.filter(reviewed=selected_state == 'bank_history')
        if selected_state != 'bank_history':
            bank_rows = bank_rows.filter(prior_to_baseline=selected_state == 'bank_prior')
        count = bank_rows.count()
    else:
        count = rows.count()
    pages = max(1, ceil(count / page_size))
    page = min(max(1, int(request.GET.get('page', 1))), pages)
    events = list(
        rows.select_related('operation', 'operation_membership__operation')
        .prefetch_related('investments__investment')
        .order_by('-facts__date', '-id')[(page - 1) * page_size : page * page_size]
    )
    op_ids = {op.pk for event in events if (op := operation_for(event)) is not None}
    operations = {
        op.pk: op
        for op in ReconciledInvestmentOperation.objects.filter(
            pk__in=op_ids, event__connection__user=request.user
        ).prefetch_related(
            Prefetch(
                'movements',
                queryset=InvestmentTransaction.objects.filter(
                    user=request.user, investment__user=request.user
                ).select_related('investment'),
            ),
            Prefetch('cash_evidence', queryset=InvestmentCashEvidence.objects.filter(connection__user=request.user)),
            Prefetch(
                'event_memberships',
                queryset=InvestmentOperationEvent.objects.filter(event__connection__user=request.user),
            ),
        )
    }

    def event_data(event):
        sources = [s for s in event.investments.all() if s.connection_id == event.connection_id]
        owned_sources = [s for s in sources if s.investment_id and s.investment.user_id == request.user.pk]
        when = event_date(event.facts)
        source_kind = classify(event.facts)[0]
        op = operation_for(event)
        op = operations.get(op.pk) if op else None
        kind = op.kind if op and event.state in resolved_states else source_kind
        if kind == 'purchase_group':
            kind = 'buy'
        candidates = []
        cash_candidates = []
        if event.state in ('new', 'historical'):
            ids = [s.investment_id for s in owned_sources]
            movement_types = {
                'buy': ('aporte', 'custo'),
                'sell': ('resgate', 'rendimento', 'custo'),
                'income': ('rendimento', 'custo'),
                'ambiguous': ('rendimento', 'custo'),
                'tax': ('custo',),
                'amortization': ('resgate', 'custo'),
                'transfer': ('aporte', 'resgate'),
            }.get(source_kind, ())
            candidates = list(
                InvestmentTransaction.objects.filter(
                    user=request.user,
                    investment_id__in=ids,
                    type__in=movement_types,
                    date__range=(when - timedelta(days=7), when + timedelta(days=7)),
                )
                .order_by('date', 'id')
                .values('id', 'date', 'type', 'amount', 'notes', 'investment__description')
            )
            if len(owned_sources) == 1:
                candidates += [
                    {**m, 'legacy': True} for m in legacy_link_candidates(request.user, event, owned_sources[0].investment)
                    .exclude(pk__in=[m['id'] for m in candidates])
                    .values('id', 'date', 'type', 'amount', 'notes', 'investment__description')
                ]
        if event.state in ('new', 'historical') and source_kind != 'transfer':
            cash_candidates = list(
                InvestmentCashEvidence.objects.filter(
                    connection_id=event.connection_id,
                    operations__isnull=True,
                    facts__type='DEBIT' if source_kind in ('buy', 'tax') else 'CREDIT',
                    facts__status='POSTED',
                    facts__currencyCode='BRL',
                    facts__date__gte=(when - timedelta(days=7)).isoformat(),
                    facts__date__lt=(when + timedelta(days=8)).isoformat(),
                ).values('id', 'facts')[:30]
            )
            if event.state == 'historical' and event.facts.get('netAmount') is not None:
                cash_candidates = [c for c in cash_candidates
                                   if abs(Decimal(str(c['facts']['amount']))) == Decimal(str(event.facts['netAmount']))]
        return {
            'id': event.pk,
            'revision': event.revision,
            'state': event.state,
            'reason': event.reason,
            'kind': kind,
            'source_kind': source_kind,
            'facts': event.facts,
            'mapped': len(sources) == 1 and len(owned_sources) == 1,
            'candidates': [{**m, 'description': m['notes']} for m in candidates],
            'cash_candidates': cash_candidates,
            'titles': [
                s.investment.description if s in owned_sources else s.facts.get('name') or 'Investimento a identificar'
                for s in sources
            ],
            'operation': {
                'id': op.pk,
                'kind': op.kind,
                'state': op.state,
                'automatic': op.automatic,
                'event_count': len({op.event_id, *(member.event_id for member in op.event_memberships.all())}),
            }
            if op
            else None,
            'matched_movements': [
                {
                    'id': m.pk,
                    'date': m.date,
                    'type': m.type,
                    'amount': m.amount,
                    'current_value': m.current_value,
                    'investment': m.investment.description,
                }
                for m in op.movements.all()
            ]
            if op
            else [],
            'settlements': [{'facts': c.facts} for c in op.cash_evidence.all()] if op else [],
        }

    credits = []
    if any(e.state == 'new' and classify(e.facts)[0] in ('buy', 'tax') for e in events):
        for credit in (
            InvestmentTransaction.objects.filter(
                user=request.user,
                investment__default_wallet_for=request.user,
                type__in=['aporte', 'rendimento'],
            )
            .prefetch_related('cash_allocations_out', 'funded_transactions')
            .order_by('-date', '-id')
        ):
            used = sum((a.amount for a in credit.cash_allocations_out.all()), 0)
            used += sum((m.amount for m in credit.funded_transactions.all()), 0)
            available = credit.amount - used
            if available > 0:
                credits.append(
                    {'id': credit.pk, 'date': credit.date, 'notes': credit.notes, 'available': str(available)}
                )
    bank_entries = []
    if selected_state in ('bank', 'bank_history', 'bank_prior'):
        from bank_sync.bank_trades import purchase_options
        from bank_sync.models import InvestmentBankTrade
        from django.db.models import Q
        for cash in bank_rows.order_by('-facts__date', '-id')[(page - 1) * page_size : page * page_size]:
            review = cash.reviews.filter(revision=cash.revision).first()
            trade = InvestmentBankTrade.objects.filter(Q(credit=cash) | Q(debit=cash)).select_related('investment__asset', 'source__investment').first()
            if trade and trade.state == 'conflict':
                review = None
            bank_entries.append({
                'id': cash.pk, 'revision': cash.revision, 'facts': cash.facts,
                'review': {'action': review.action, 'evidence': review.evidence,
                           'automatic': review.automatic} if review else None,
                'prior_to_baseline': cash.prior_to_baseline,
                'previously_reviewed': not review and cash.reviews.exists(),
                'purchase_options': purchase_options(cash) if not review else [],
                'trade': {'id': trade.pk, 'state': trade.state, 'investment': trade.investment.description,
                          'symbol': trade.investment.asset.symbol, 'quantity': format(trade.quantity, 'f'),
                          'amount': str(trade.amount), 'source': trade.source.investment.description} if trade else None,
                'candidates': [
                    {'id': m.pk, 'date': m.date, 'amount': m.amount,
                     'type': m.type, 'current_value': m.current_value,
                     'investment': m.investment.description, 'broker': m.investment.broker.description}
                    for m in (review.movements.select_related('investment__broker').all()
                              if review else cash_movements(request.user, cash))
                ],
            })
        for entry in bank_entries:
            for option in entry['purchase_options']:
                for related in bank_entries:
                    if related['id'] == option['credit_id']:
                        related['funding_for_debit'] = entry['id']
    return JsonResponse(
        {
            'credits': credits,
            'count': count,
            'page': page,
            'pages': pages,
            'page_size': page_size,
            'filter': selected_state,
            'summary': summary,
            'events': [event_data(event) for event in events],
            'bank_entries': bank_entries,
            'jobs': list(
                InvestmentHistoryJob.objects.filter(connection__user=request.user)
                .order_by('-id')
                .values('id', 'state', 'message', 'progress', 'finished_at')[:5]
            ),
        }
    )


@login_required
@require_POST
@api_errors
def bank_review(request, pk):
    data = body(request)
    if data.get('action') == 'keep':
        from bank_sync.bank_trades import keep_bank_trade
        trade = keep_bank_trade(request.user, pk, int(data['revision']), data.get('evidence', ''))
        return JsonResponse({'trade_id': trade.pk})
    review = review_cash(request.user, pk, int(data['revision']), data['action'],
                         data.get('movement_id'), data.get('evidence', ''))
    return JsonResponse({'review_id': review.pk})


@login_required
@require_POST
@api_errors
def bank_purchase(request, pk):
    from bank_sync.bank_trades import register_purchase
    data = body(request)
    trade = register_purchase(request.user, pk, int(data['revision']), int(data['source_id']),
                              int(data['credit_id']), data['symbol'], data['quantity'], data.get('evidence', ''))
    return JsonResponse({'trade_id': trade.pk, 'investment_id': trade.investment_id,
                         'quantity': format(trade.quantity, 'f'), 'amount': str(trade.amount)})


@login_required
@require_POST
@api_errors
def auto_link(request):
    from bank_sync.auto_reconciliation import auto_reconcile
    from bank_sync.event_import import import_events
    connections = BankConnection.objects.filter(user=request.user).select_related('user')
    if connections.count() != 1:
        raise ValidationError('Selecione uma conexão inequívoca.')
    with transaction.atomic():
        connection = connections.get()
        result = auto_reconcile(connection)
        imported = import_events(connection)
    return JsonResponse({'events': len(result['events']), 'bank_entries': len(result['bank_entries']),
                         'registered': len(imported['applied']), 'adopted': len(imported['adopted'])})


@login_required
@require_POST
@api_errors
def enqueue(request):
    from bank_sync.history_queue import queue_history
    with transaction.atomic():
        connections = BankConnection.objects.select_for_update().filter(user=request.user)
        if connections.count() != 1:
            raise ValidationError('Selecione uma conexão inequívoca.')
        connection = connections.get()
        job = queue_history(connection)
    return JsonResponse({'job_id': job.pk, 'state': job.state}, status=202)


@login_required
@require_POST
@api_errors
def review(request, pk):
    data = body(request)
    if len(data.get('events', [])) > 1:
        if data.get('action') != 'apply':
            raise ValidationError('Desmarque o grupo para vincular ou ignorar individualmente.')
        from bank_sync.investment_events import (
            reconcile_purchase_group,
            reconcile_transfer_group,
        )

        kinds = list(
            InvestmentEvent.objects.filter(
                connection__user=request.user,
                pk__in=[x['id'] for x in data['events']],
            ).values_list('facts__type', flat=True)
        )
        if kinds and all(k == 'TRANSFER' for k in kinds):
            op = reconcile_transfer_group(
                request.user,
                data['events'],
                data.get('principal'),
                data.get('evidence', ''),
            )
            return JsonResponse({'operation_id': op.pk})
        op = reconcile_purchase_group(
            request.user,
            data['events'],
            data.get('cash_ids', []),
            data.get('allocations', []),
            data.get('shared_cost', '0'),
            data.get('evidence', ''),
        )
        return JsonResponse({'operation_id': op.pk})
    op = reconcile(
        request.user,
        pk,
        int(data['revision']),
        data['action'],
        movement_ids=data.get('movement_ids', []),
        funding_ids=data.get('funding_ids', []),
        principal=data.get('principal'),
        evidence=data.get('evidence', ''),
        expected_kind=data.get('kind'),
        allocations=data.get('allocations', []),
        cash_ids=data.get('cash_ids', []),
    )
    return JsonResponse({'operation_id': op.pk if op else None})
