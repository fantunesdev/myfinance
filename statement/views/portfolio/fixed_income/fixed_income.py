from statement.forms.portfolio.fixed_income.fixed_income import FixedIncomeForm
from statement.models import FixedIncome
from statement.services.portfolio.fixed_income.fixed_income import FixedIncomeService
from statement.views.base_view import BaseView


class FixedIncomeView(BaseView):
    """
    View responsável pela gestão da Renda Variável
    """

    class_has_user = True
    class_title = 'Renda Variável'
    column_names = ['Conta', 'Papel']
    class_form = FixedIncomeForm
    model = FixedIncome
    service = FixedIncomeService
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
