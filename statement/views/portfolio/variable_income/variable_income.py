from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from statement.forms.portfolio.variable_income.variable_income import VariableIncomeForm
from statement.models import VariableIncome
from statement.services.portfolio.variable_income.variable_income import VariableIncomeService
from statement.views.base_view import BaseView

class VariableIncomeView(BaseView):
    class_has_user = True
    class_title = 'renda variável'
    column_names = ['Conta', 'Papel']
    form_class = VariableIncomeForm
    model = VariableIncome
    service = VariableIncomeService
    redirect_url = 'get_variable_income'
