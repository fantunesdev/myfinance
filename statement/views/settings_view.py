from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from statement.services.core.account import AccountService
from statement.services.core.bank import BankService
from statement.services.core.card import CardService
from statement.services.core.category import CategoryService
from statement.services.core.fixed_expenses import FixedExpensesService
from statement.services.core.flag import FlagService
from statement.services.core.subcategory import SubcategoryService
from statement.services.next_month_view import NextMonthViewService
from statement.services.portfolio.fixed_income.index import IndexService
from statement.services.portfolio.fixed_income.security import FixedIncomeSecurityService
from statement.services.portfolio.variable_income.sector import SectorService
from statement.services.portfolio.variable_income.ticker import TickerService
from statement.views.base_view import BaseView


class SettingsView(BaseView):
    """
    View responsável pela gestão das configurações
    """

    redirect_url = 'setup_settings'

    @method_decorator(login_required)
    def settings(self, request):
        """
        Retorna todas as instâncias do modelo.
        """
        specific_content = {
            'accounts': AccountService.get_all(request.user),
            'next_month_view': NextMonthViewService.get_all(request.user).first(),
            'banks': BankService.get_all(),
            'flags': FlagService.get_all(),
            'cards': CardService.get_all(request.user),
            'categories': CategoryService.get_all(),
            'subcategories': SubcategoryService.get_all(),
            'fixed_expenses': FixedExpensesService.get_all(request.user),

            # Renda Fixa
            'indexes': IndexService.get_all(request.user),
            'fixed_income_securities': FixedIncomeSecurityService.get_all(request.user),

            # Renda Variável
            'sectors': SectorService.get_all(request.user),
            'tickers': TickerService.get_all(request.user),
        }
        return self._render(request, None, 'general/setup_settings.html', specific_content)
