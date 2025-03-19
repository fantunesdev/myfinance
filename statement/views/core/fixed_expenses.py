
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from statement.forms.core.fixed_expenses import FixedExpensesForm
from statement.models import FixedExpenses
from statement.services.core.fixed_expenses import FixedExpensesService
from statement.services.core.transaction import TransactionService
from statement.views.core.transaction import TransactionView
from statement.utils.datetime import DateTimeUtils


class FixedExpensesView(TransactionView):
    """
    View responsável pela gestão das despesas fixas
    """

    class_has_user = True
    class_title = 'Conta'
    class_form = FixedExpensesForm
    model = FixedExpenses
    service = FixedExpensesService
    redirect_url = 'get_current_month_transactions'

    @method_decorator(login_required)
    def get_by_year_and_month(self, request, year, month):
        """
        View responsável por exibir os lançamentos de um ano e mês específicos.
        """
        filters = self._set_monthly_filter_by_date_attr('payment', request.user, year, month, home_screen=True)
        filters.update(self._set_additional_filters())
        instances = TransactionService.get_by_filter(**filters)
        fixed_expenses = FixedExpensesService.get_active_by_date(year, month, request.user)
        specific_context = self._set_specific_context(instances, year, month, fixed_expenses=fixed_expenses)
        return self._render(request, None, 'transaction/list.html', specific_context)
