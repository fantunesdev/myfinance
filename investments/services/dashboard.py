"""JSON contract for the dashboard. Accounting stays in InvestmentService."""
from decimal import Decimal

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
                'label': str(position['investment']),
                'asset_type': position['asset_type'],
                'asset_type_label': position['asset_type_label'],
                'broker': str(position['broker']),
                'quantity': str(position['quantity']),
                'value': str(position['value']),
                'url': reverse('detail_investment', args=[position['investment'].pk]),
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
    from bank_sync.models import InvestmentHistoryJob, InvestmentEvent
    from investments.models import InvestmentTransaction

    if InvestmentHistoryJob.objects.filter(connection__user=user).exists():
        recognized = (
            InvestmentTransaction.objects.filter(
                user=user,
                type__in=['rendimento', 'custo'],
                reconciled_operations__state__in=['applied', 'linked'],
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
        price = InvestmentService.get_average_purchase_price(position['investment'])
        record['average_purchase_price'] = str(price) if price is not None else None
    return payload
