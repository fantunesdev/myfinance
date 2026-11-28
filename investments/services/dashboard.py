"""JSON contract for the dashboard. Accounting stays in InvestmentService."""
from decimal import Decimal
from django.db.models import F, Q

from django.urls import reverse
from django.utils import timezone

from investments.models import Broker
from investments.services.investment import InvestmentService
from investments.services.transaction import InvestmentTransactionService


def dashboard_payload(user, revision):
    dashboard = InvestmentService.get_dashboard(user)
    positions = dashboard['positions']
    broker_values = dict(dashboard['by_broker'])
    payload = {
        'schema_version': 1,
        'user_id': user.pk,
        'revision': revision,
        'generated_at': timezone.now().isoformat(),
        'totals': {
            'total': str(dashboard['total']),
            'net_income': str(dashboard['net_income']),
            'available_to_invest': str(
                sum(
                    (position['value'] for position in positions if position['asset_type'] == 'currency'),
                    Decimal('0'),
                )
            ),
        },
        'positions': [
            {
                'id': position['investment'].pk,
                'label': position.get('label', str(position['investment'])),
                'asset_type': position['asset_type'],
                'asset_type_label': position['asset_type_label'],
                'broker': str(position['broker']),
                'quantity': str(position['quantity']),
                'value': str(position['value']),
                'url': reverse('detail_investment_product', args=[position['product'].pk]) if position.get('product') else reverse('detail_investment', args=[position['investment'].pk]),
                'lot_count': len(position.get('lots', [position])),
                'is_portfolio': position.get('product') is not None and position['product'].kind == 'portfolio',
                'valuation': {'date': position['valuation'].date.isoformat(), 'source': position['valuation'].source,
                    'basis': position['valuation'].basis, 'value': str(position['valuation'].value)} if position.get('valuation') else None,
            }
            for position in positions
        ],
        'brokers': [
            {
                'id': broker.pk,
                'label': broker.description,
                'value': str(broker_values.get(broker.description, Decimal('0'))),
            }
            for broker in Broker.objects.filter(user=user)
        ],
        'progression_datasets': dashboard['progression_datasets'],
        'interest_datasets': dashboard['interest_datasets'],
        'has_default_wallet': InvestmentTransactionService.get_default_wallet(user) is not None,
    }
    from bank_sync.models import ExternalInvestment, InvestmentHistoryJob, InvestmentEvent
    from investments.models import InvestmentTransaction

    # Keep unmapped source balances visible without treating them as new money:
    # they can overlap a local position or represent a pending reinvestment.
    unmapped = []
    for external in ExternalInvestment.objects.filter(connection__user=user, investment__isnull=True):
        facts = external.facts
        if facts.get('status') != 'ACTIVE':
            continue
        try:
            balance = Decimal(str(facts.get('balance')))
        except (ValueError, ArithmeticError):
            continue
        if not balance.is_finite() or balance <= 0:
            continue
        unmapped.append({
            'id': external.pk,
            'label': facts.get('name') or 'Posição sem vínculo',
            'currency': facts.get('currencyCode'),
            'value': str(balance),
            'reference_at': facts.get('date'),
        })
    payload['source_coverage'] = {'unmapped_positions': unmapped}

    if InvestmentHistoryJob.objects.filter(connection__user=user).exists():
        recognized = (
            InvestmentTransaction.objects.filter(
                user=user,
                type__in=['rendimento', 'custo'],
            ).filter(
                Q(reconciled_operations__state__in=['applied', 'linked'])
                | Q(bank_cash_reviews__action='apply', bank_cash_reviews__trade__state='applied',
                    bank_cash_reviews__revision=F('bank_cash_reviews__cash__revision'))
            )
            .values('id', 'type', 'amount')
            .distinct()
        )
        confirmed = sum(
            (row['amount'] if row['type'] == 'rendimento' else -row['amount'] for row in recognized),
            Decimal('0'),
        )
        payload['totals']['confirmed_net_income'] = str(confirmed)
        payload['totals']['legacy_net_income'] = str(dashboard['net_income'] - confirmed)
        payload['reconciliation_pending'] = InvestmentEvent.objects.filter(
            connection__user=user, state__in=['new', 'historical', 'conflict']
        ).count()
    for position, record in zip(positions, payload['positions']):
        price = None if position.get('product') else InvestmentService.get_average_purchase_price(position['investment'])
        record['average_purchase_price'] = str(price) if price is not None else None
    return payload
