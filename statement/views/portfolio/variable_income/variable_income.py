from statement.forms.portfolio.variable_income.variable_income import VariableIncomeForm
from statement.models import VariableIncome
from statement.services.portfolio.variable_income.variable_income import VariableIncomeService
from statement.views.base_view import BaseView


class VariableIncomeView(BaseView):
    """
    View responsável pela gestão da Renda Variável
    """

    class_has_user = True
    class_title = 'Renda Variável'
    column_names = ['Conta', 'Papel']
    class_form = VariableIncomeForm
    model = VariableIncome
    service = VariableIncomeService
    redirect_url = 'get_variable_income'

    def __init__(self):
        """
        Atualiza o dicionário actions_list sem sobrescrever toda a estrutura da classe base.
        """
        super().__init__()
        self.actions_list.update(
            {
                'detail': False,
            }
        )
