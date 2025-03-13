from decimal import Decimal

from django.db.models import Sum

from statement.models import AssetTransaction
from statement.services.base_service import BaseService


class AssetTransactionService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo AssetTransaction."""

    model = AssetTransaction
    field_user = 'user'

    @staticmethod
    def calculate_quantity_at_date(variable_income, date):
        """Calcula a quantidade de ações restantes até uma data específica."""
        # Transações de compra
        bought_quantity = AssetTransaction.objects.filter(
            variable_income=variable_income,
            transaction_type='buy',
            date__lte=date
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0

        # Transações de venda
        sold_quantity = AssetTransaction.objects.filter(
            variable_income=variable_income,
            transaction_type='sell',
            date__lte=date
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0

        return bought_quantity - sold_quantity

    @staticmethod
    def calculate_average_buy_value(variable_income, date):
        """Calcula o preço médio de compra até uma data específica."""
        # Transações de compra
        buy_transactions = AssetTransaction.objects.filter(
            variable_income=variable_income,
            transaction_type='buy',
            date__lte=date
        )

        # Transações de venda
        sell_transactions = AssetTransaction.objects.filter(
            variable_income=variable_income,
            transaction_type='sell',
            date__lte=date
        )

        # Quantidade total comprada até a data
        total_quantity_bought = buy_transactions.aggregate(Sum('quantity'))['quantity__sum'] or 0

        # Quantidade total vendida até a data
        total_quantity_sold = sell_transactions.aggregate(Sum('quantity'))['quantity__sum'] or 0

        # A quantidade atual de ações compradas (não vendidas)
        remaining_quantity = total_quantity_bought - total_quantity_sold

        if remaining_quantity <= 0:
            return Decimal(0)  # Se não houver ações restantes, o preço médio é 0

        # Total gasto nas compras até a data
        total_spent = buy_transactions.aggregate(Sum('value'))['value__sum'] or Decimal(0)

        # Calculando o preço médio
        average_buy_value = total_spent / remaining_quantity
        return average_buy_value
