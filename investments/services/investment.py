from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
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
    def delete(cls, instance):
        with transaction.atomic():
            from investments.services.transaction import InvestmentTransactionService

            InvestmentTransactionService.lock_user(instance.user)
            if instance.default_wallet_for_id or instance.transactions.exists():
                raise ValidationError(
                    'Investimentos com histórico e o caixa padrão não podem ser excluídos. Encerre o investimento para preservar as movimentações.'
                )
            return super().delete(instance)

    @staticmethod
    def apply_value(value, movement):
        if not movement.affects_value:
            return value
        if movement.type in ('aporte', 'rendimento'):
            return value + movement.amount
        if movement.type in ('resgate', 'custo'):
            return value - movement.amount
        if movement.type == 'atualizacao' and movement.current_value is not None:
            return movement.current_value
        return value

    @classmethod
    def get_position(cls, investment, as_of=None, exclude_ids=()):
        movements = sorted(
            (
                item
                for item in investment.transactions.all()
                if item.user_id == investment.user_id
                and item.pk not in exclude_ids
                and (as_of is None or item.date <= as_of)
            ),
            key=lambda item: (item.date, item.pk),
        )
        invested = income = costs = withdrawn = quantity = value = Decimal('0')
        withdrawn_principal = Decimal('0')
        for movement in movements:
            amount = movement.amount or Decimal('0')
            value = cls.apply_value(value, movement)
            if movement.type == 'aporte':
                invested += amount
                quantity += movement.quantity or Decimal('0')
            elif movement.type == 'resgate':
                withdrawn += amount
                withdrawn_principal += (
                    movement.redemption_principal if movement.redemption_principal is not None else amount
                )
                quantity -= movement.quantity or Decimal('0')
            elif movement.type == 'rendimento':
                income += amount
            elif movement.type == 'custo':
                costs += amount
            elif movement.type == 'atualizacao' and movement.quantity is not None:
                quantity = movement.quantity
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
            'remaining_principal': invested - withdrawn_principal,
            'unwithdrawn_income': sum((m.amount if m.type == 'rendimento' else -m.amount for m in movements if m.affects_value and m.type in ('rendimento', 'custo')), Decimal('0')) - (withdrawn - withdrawn_principal),
        }

    @staticmethod
    def get_average_purchase_price(investment):
        """Moving weighted average of purchase amounts, independent of valuation.

        Purchase amounts include any charges recorded in that amount. Generic
        fee/tax movements cannot be attributed to purchases and are excluded.
        Missing trade quantities make the result unavailable.
        """
        if investment.asset.asset_type not in ('variable_income', 'crypto'):
            return None

        quantity = average_price = Decimal('0')
        movements = sorted(
            (
                movement for movement in investment.transactions.all()
                if movement.user_id == investment.user_id and movement.type in ('aporte', 'resgate', 'atualizacao')
            ),
            key=lambda movement: (movement.date, movement.pk),
        )
        for movement in movements:
            units = movement.quantity
            if movement.type == 'atualizacao':
                if units is not None and units != quantity:
                    return None
                continue
            if units is None or units <= 0:
                return None
            if movement.type == 'aporte':
                if movement.amount <= 0:
                    return None
                average_price = (average_price * quantity + movement.amount) / (quantity + units)
                quantity += units
            else:
                if units > quantity:
                    return None
                quantity -= units
                if quantity == 0:
                    average_price = Decimal('0')
        return average_price if quantity > 0 else None

    @classmethod
    def get_position_history(cls, investment):
        today = timezone.localdate()
        movements = sorted(
            (item for item in investment.transactions.all() if item.user_id == investment.user_id and item.date <= today),
            key=lambda item: (item.date, item.pk),
        )
        value = Decimal('0')
        daily_values = {}
        for movement in movements:
            value = cls.apply_value(value, movement)
            daily_values[movement.date] = value
        if daily_values:
            daily_values[today] = value
        return {
            'dates': [day.isoformat() for day in daily_values],
            'values': [float(amount) for amount in daily_values.values()],
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
            investment.id: investment for investment in cls.filter_by_user(user).select_related('asset', 'broker')
        }
        transactions = (
            InvestmentTransaction.objects.filter(investment__user=user, user=user)
            .select_related('investment__asset')
            .order_by('date', 'id')
        )
        investment_values = defaultdict(Decimal)
        snapshots_by_date = {}

        for transaction in transactions:
            investment_values[transaction.investment_id] = cls.apply_value(
                investment_values[transaction.investment_id],
                transaction,
            )
            snapshots_by_date[transaction.date] = cls._build_progression_snapshot(investments, investment_values)

        labels = [date.strftime('%d/%m/%Y') for date in snapshots_by_date.keys()]
        asset_type_labels = sorted({investment.asset.get_asset_type_display() for investment in investments.values()})
        colors = {
            'Renda fixa': 'rgba(139, 0, 0, 1)',
            'Renda variável': 'rgba(190, 0, 0, 1)',
            'Cripto': 'rgba(165, 0, 0, 1)',
            'Moeda': 'rgba(94, 0, 0, 1)',
            'Outro': 'rgba(120, 120, 120, 1)',
        }

        return [
            {
                'label': label,
                'color': colors.get(label, 'rgba(120, 120, 120, 1)'),
                'names': labels,
                'values': [float(snapshot.get(label, Decimal('0'))) for snapshot in snapshots_by_date.values()],
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
        transactions = InvestmentTransaction.objects.filter(
            investment__user=user, user=user, type__in=['rendimento', 'custo']
        ).order_by('date', 'id')
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
                'label': 'Ganhos',
                'color': 'rgba(46, 125, 90, 1)',
                'names': labels,
                'values': income_values,
            },
            {
                'label': 'Custos',
                'color': 'rgba(139, 0, 0, 1)',
                'names': labels,
                'values': cost_values,
            },
            {
                'label': 'Resultado',
                'color': 'rgba(42, 92, 148, 1)',
                'names': labels,
                'values': net_values,
            },
        ]
