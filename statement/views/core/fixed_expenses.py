from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from statement.forms.core.fixed_expenses import FixedExpensesForm
from statement.models import FixedExpenses
from statement.services.core.fixed_expenses import FixedExpensesService
from statement.services.core.transaction import TransactionService
from statement.utils.datetime import DateTimeUtils
from statement.views.core.transaction import TransactionView


class FixedExpensesView(TransactionView):
    """
    View responsável pela gestão das despesas fixas
    """

    class_has_user = True
    class_title = 'Despesa Fixa'
    class_form = FixedExpensesForm
    model = FixedExpenses
    service = FixedExpensesService
    redirect_url = 'get_profile'
    template_is_global = {
        'create': True,
        'delete': True,
        'detail': True,
        'get_all': True,
        'update': True,
    }

    def __init__(self):
        # garante que template_is_global seja o desejado após TransactionView.__init__
        super().__init__()
        self.template_is_global.update(
            {
                'create': True,
                'delete': True,
                'detail': True,
                'get_all': True,
                'update': True,
            }
        )

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

    def create(self, request, id=None):
        """Wrapper to call TransactionView.create with a default type for fixed expenses."""
        return super().create(request, type='saida', id=id)
