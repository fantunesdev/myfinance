import json
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from bank_sync.models import (
    BankConnection,
    InvestmentEvent,
    InvestmentHistoryJob,
    InvestmentCashEvidence,
)
from bank_sync.views import api_errors, body
from bank_sync.investment_events import reconcile, classify, event_date
from investments.models import InvestmentTransaction


@login_required
def event_page(request):
    return render(request, 'bank_sync/investment_events.html')


@login_required
@require_GET
@api_errors
def event_list(request):
    rows = (
        InvestmentEvent.objects.filter(connection__user=request.user)
        .prefetch_related('investments__investment')
        .order_by('-id')
    )
    if request.GET.get('state'):
        rows = rows.filter(state=request.GET['state'])
    page = max(1, int(request.GET.get('page', 1)))
    count = rows.count()

    def candidates(event):
        from bank_sync.investment_events import event_date

        ids = [s.investment_id for s in event.investments.all() if s.investment_id]
        when = event_date(event.facts)
        return list(
            InvestmentTransaction.objects.filter(
                user=request.user,
                investment_id__in=ids,
                date__range=(
                    when - timedelta(days=7),
                    when + timedelta(days=7),
                ),
            )
            .order_by('date')
            .values('id', 'date', 'type', 'amount', 'notes')
        )

    credits = []
    for credit in InvestmentTransaction.objects.filter(
        user=request.user,
        investment__default_wallet_for=request.user,
        type__in=['aporte', 'rendimento'],
    ):
        used = credit.cash_allocations_out.aggregate(v=Sum('amount'))['v'] or 0
        legacy = sum((m.amount for m in credit.funded_transactions.all()), 0)
        available = credit.amount - used - legacy
        if available > 0:
            credits.append(
                {
                    'id': credit.pk,
                    'date': credit.date,
                    'notes': credit.notes,
                    'available': str(available),
                }
            )
    return JsonResponse(
        {
            'credits': credits,
            'count': count,
            'page': page,
            'events': [
                {
                    'id': x.pk,
                    'revision': x.revision,
                    'state': x.state,
                    'reason': x.reason,
                    'kind': classify(x.facts)[0],
                    'facts': x.facts,
                    'candidates': [{**m, 'description': m.pop('notes', '')} for m in candidates(x)],
                    'cash_candidates': list(
                        InvestmentCashEvidence.objects.filter(
                            connection=x.connection,
                            operations__isnull=True,
                            facts__date__gte=(event_date(x.facts) - timedelta(days=7)).isoformat(),
                            facts__date__lt=(event_date(x.facts) + timedelta(days=8)).isoformat(),
                        ).values('id', 'facts')[:30]
                    ),
                    'titles': [
                        i.investment.description if i.investment_id else str(i.external_id) for i in x.investments.all()
                    ],
                }
                for x in rows[(page - 1) * 30 : page * 30]
            ],
            'jobs': list(
                InvestmentHistoryJob.objects.filter(connection__user=request.user)
                .order_by('-id')
                .values('id', 'state', 'message', 'progress')[:5]
            ),
        }
    )


@login_required
@require_POST
@api_errors
def enqueue(request):
    with transaction.atomic():
        connections = BankConnection.objects.select_for_update().filter(user=request.user)
        if connections.count() != 1:
            raise ValidationError('Selecione uma conexão inequívoca.')
        connection = connections.get()
        now = timezone.now()
        InvestmentHistoryJob.objects.filter(connection=connection, state='running', lease_until__lt=now).update(
            state='failed',
            message='Execução interrompida; uma nova coleta pode ser solicitada.',
        )
        job = InvestmentHistoryJob.objects.filter(connection=connection, state__in=['queued', 'running']).first()
        if not job:
            job = InvestmentHistoryJob.objects.create(connection=connection)
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
