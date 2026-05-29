from collections import defaultdict
from decimal import Decimal

from investments.models import Investment, InvestmentTransaction
from investments.services.base import InvestmentBaseService


class InvestmentService(InvestmentBaseService):
    model = Investment

    @classmethod
    def get_active(cls, user):
        return cls.filter_by_user(user).filter(status='active')

    @classmethod
    def get_positions(cls, user):
        investments = cls.filter_by_user(user).select_related('asset', 'broker').prefetch_related('transactions')
        return [cls.get_position(investment) for investment in investments]

    @classmethod
    def get_position(cls, investment):
        invested = Decimal('0')
        income = Decimal('0')
        costs = Decimal('0')
        withdrawn = Decimal('0')
        quantity = Decimal('0')
        current_value = None

        for transaction in investment.transactions.all():
            amount = transaction.amount or Decimal('0')
            match transaction.type:
                case 'aporte':
                    invested += amount
                    quantity += transaction.quantity or Decimal('0')
                case 'resgate':
                    withdrawn += amount
                    quantity -= transaction.quantity or Decimal('0')
                case 'rendimento':
                    income += amount
                case 'custo':
                    costs += amount
                case 'atualizacao':
                    if transaction.current_value is not None:
                        current_value = transaction.current_value

        calculated_value = invested + income - withdrawn - costs
        value = current_value if current_value is not None else calculated_value

        return {
            'investment': investment,
            'asset': investment.asset,
            'broker': investment.broker,
            'asset_type': investment.asset.asset_type,
            'asset_type_label': investment.asset.get_asset_type_display(),
            'invested': invested,
            'income': income,
            'costs': costs,
            'withdrawn': withdrawn,
            'quantity': quantity,
            'value': value,
        }

    @classmethod
    def get_dashboard(cls, user):
        positions = cls.get_positions(user)
        total = sum((position['value'] for position in positions), Decimal('0'))
        by_type = defaultdict(Decimal)
        by_broker = defaultdict(Decimal)

        for position in positions:
            by_type[position['asset_type_label']] += position['value']
            by_broker[position['broker'].description] += position['value']

        total_income = sum((position['income'] for position in positions), Decimal('0'))
        total_costs = sum((position['costs'] for position in positions), Decimal('0'))

        return {
            'positions': positions,
            'total': total,
            'total_income': total_income,
            'total_costs': total_costs,
            'net_income': total_income - total_costs,
            'by_type': sorted(by_type.items()),
            'by_broker': sorted(by_broker.items()),
            'progression_datasets': cls.get_progression_datasets(user),
            'interest_datasets': cls.get_interest_datasets(user),
        }

    @classmethod
    def get_progression_datasets(cls, user):
        investments = {
            investment.id: investment
            for investment in cls.filter_by_user(user).select_related('asset', 'broker')
        }
        transactions = (
            InvestmentTransaction.objects.filter(investment__user=user)
            .select_related('investment__asset')
            .order_by('date', 'id')
        )
        investment_values = defaultdict(Decimal)
        snapshots_by_date = {}

        for transaction in transactions:
            current_value = investment_values[transaction.investment_id]
            amount = transaction.amount or Decimal('0')

            match transaction.type:
                case 'aporte' | 'rendimento':
                    current_value += amount
                case 'resgate' | 'custo':
                    current_value -= amount
                case 'atualizacao':
                    if transaction.current_value is not None:
                        current_value = transaction.current_value

            investment_values[transaction.investment_id] = current_value
            snapshots_by_date[transaction.date] = cls._build_progression_snapshot(investments, investment_values)

        labels = [date.strftime('%d/%m/%Y') for date in snapshots_by_date.keys()]
        asset_type_labels = sorted(
            {
                investment.asset.get_asset_type_display()
                for investment in investments.values()
            }
        )
        colors = {
            'Renda fixa': 'rgba(46, 125, 90, 1)',
            'Renda variável': 'rgba(139, 0, 0, 1)',
            'Cripto': 'rgba(255, 191, 0, 1)',
            'Moeda': 'rgba(42, 92, 148, 1)',
            'Outro': 'rgba(120, 120, 120, 1)',
        }

        return [
            {
                'label': label,
                'color': colors.get(label, 'rgba(120, 120, 120, 1)'),
                'names': labels,
                'values': [
                    float(snapshot.get(label, Decimal('0')))
                    for snapshot in snapshots_by_date.values()
                ],
            }
            for label in asset_type_labels
        ]

    @staticmethod
    def _build_progression_snapshot(investments, investment_values):
        snapshot = defaultdict(Decimal)
        for investment_id, value in investment_values.items():
            investment = investments.get(investment_id)
            if not investment:
                continue
            snapshot[investment.asset.get_asset_type_display()] += value
        return snapshot

    @classmethod
    def get_interest_datasets(cls, user):
        transactions = (
            InvestmentTransaction.objects.filter(investment__user=user, type__in=['rendimento', 'custo'])
            .order_by('date', 'id')
        )
        labels = []
        income_values = []
        cost_values = []
        net_values = []
        income = Decimal('0')
        costs = Decimal('0')

        for transaction in transactions:
            amount = transaction.amount or Decimal('0')
            if transaction.type == 'rendimento':
                income += amount
            else:
                costs += amount

            labels.append(transaction.date.strftime('%d/%m/%Y'))
            income_values.append(float(income))
            cost_values.append(float(costs * Decimal('-1')))
            net_values.append(float(income - costs))

        return [
            {
                'label': 'Rendimentos acumulados',
                'color': 'rgba(46, 125, 90, 1)',
                'names': labels,
                'values': income_values,
            },
            {
                'label': 'Custos acumulados',
                'color': 'rgba(139, 0, 0, 1)',
                'names': labels,
                'values': cost_values,
            },
            {
                'label': 'Juros líquidos',
                'color': 'rgba(42, 92, 148, 1)',
                'names': labels,
                'values': net_values,
            },
        ]
