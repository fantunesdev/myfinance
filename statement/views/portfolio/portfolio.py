from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from statement.services.portfolio.fixed_income.fixed_income import FixedIncomeService
from statement.views.base_view import BaseView


class PortfolioView(BaseView):
    """
    View responsável pela exibição da carteira
    """

    @method_decorator(login_required)
    def get_portfolio(self, request):
        """
        Obtém dados gerais do patrimônio
        """
        total_fixed_income = FixedIncomeService.get_total_amount(request.user)
        total_variable_income = 0
        total_cryptocurrencies = 0
        total_amount = total_fixed_income + total_variable_income + total_cryptocurrencies
        specific_content = {
            'total_fixed_income': total_fixed_income,
            'total_variable_income': total_variable_income,
            'total_cryptocurrencies': total_cryptocurrencies,
            'total_amount': total_amount,
        }
        return self._render(request, None, 'portfolio/get_portfolio.html', specific_content)
