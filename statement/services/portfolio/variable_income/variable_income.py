import datetime

from statement.models import VariableIncome
from statement.services.base_service import BaseService
from statement.services.portfolio.variable_income.asset_transaction import AssetTransactionService


class VariableIncomeService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo VariableIncome."""

    model = VariableIncome
    field_user = 'user'

    @staticmethod
    def get_status(variable_income):
        """Calcula o status do ativo com base nas transações"""
        today = datetime.date.today()
        bought_quantety = AssetTransactionService.calculate_quantity_at_date(variable_income, today)

        if bought_quantety > 0:
            return 'active'
        return 'sold'

    @staticmethod
    def get_averange_buy_vaule(variable_income):
        today = datetime.date.today()
        return AssetTransactionService.calculate_average_buy_value(variable_income, today)
