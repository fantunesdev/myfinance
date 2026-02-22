from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from statement.services.core.account import AccountService
from statement.services.core.bank import BankService
from statement.services.core.card import CardService
from statement.services.core.category import CategoryService
from statement.services.core.flag import FlagService
from statement.services.core.subcategory import SubcategoryService
from statement.services.core.fixed_expenses import FixedExpensesService
from statement.models import AppConfig
from statement.services.portfolio.fixed_income.index import IndexService
from statement.services.portfolio.fixed_income.security import FixedIncomeSecurityService
from statement.services.portfolio.variable_income.sector import SectorService
from statement.services.portfolio.variable_income.ticker import TickerService
from statement.views.base_view import BaseView
from django.forms import modelform_factory
from django.shortcuts import redirect


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
        # Resolve app config flag safely to avoid crashing if migrations are not applied yet
        try:
            enable_transaction_classifier = AppConfig.get_solo().enable_transaction_classifier
        except Exception:
            enable_transaction_classifier = False

        specific_content = {
            'accounts': AccountService.get_all(request.user),
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
            'app_config_enable_transaction_classifier': enable_transaction_classifier,
        }
        return self._render(request, None, 'general/setup_settings.html', specific_content)

    @method_decorator(login_required)
    def edit_app_config(self, request):
        """Edit global AppConfig (enable_transaction_classifier) from settings UI."""
        try:
            cfg = AppConfig.get_solo()
        except Exception:
            # If table doesn't exist yet, create an in-memory default instance
            cfg = AppConfig()

        AppConfigForm = modelform_factory(AppConfig, fields=('enable_transaction_classifier',))
        if request.method == 'POST':
            form = AppConfigForm(request.POST, instance=cfg)
            if form.is_valid():
                form.save()
                return redirect('setup_settings')
        else:
            form = AppConfigForm(instance=cfg)

        # reuse global base form template
        return self._render(request, form, 'base/form.html', {})
