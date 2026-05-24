from collections import defaultdict
from decimal import Decimal

from investments.models import Investment
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

        return {
            'positions': positions,
            'total': total,
            'by_type': sorted(by_type.items()),
            'by_broker': sorted(by_broker.items()),
        }
