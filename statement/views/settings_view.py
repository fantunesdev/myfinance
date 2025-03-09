from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from statement.models import FixedIncomeSecurity
from statement.repositories.templatetags_repository import set_menu_templatetags, set_templatetags
from statement.services.category import CategoryService
from statement.services.subcategory import SubcategoryService
from statement.services.index_services import IndexServices
from statement.services.portfolio.variable_income.sector import SectorService
from statement.services.portfolio.variable_income.ticker import TickerService
from statement.services import (
    account_services,
    bank_services,
    card_services,
    fixed_expenses_services,
    flag_services,
    next_month_view_services,
)


@login_required
def setup_settings(request):
    """
    Recupera todas as configurações
    """
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['accounts'] = account_services.get_accounts(request.user)
    templatetags['next_month_view'] = next_month_view_services.get_next_month_view_by_user(request.user)
    templatetags['banks'] = bank_services.get_banks()
    templatetags['flags'] = flag_services.get_flags()
    templatetags['cards'] = card_services.get_cards(request.user)
    templatetags['categories'] = CategoryService.get_all()
    templatetags['subcategories'] = SubcategoryService.get_all()
    templatetags['fixed_expenses'] = fixed_expenses_services.get_fixed_expenses(request.user)

    # Renda Fixa
    templatetags['indexes'] = IndexServices.all()
    templatetags['fixed_income_securities'] = FixedIncomeSecurity.objects.all()

    # Renda Variável
    templatetags['sectors'] = SectorService.get_all()
    templatetags['tickers'] = TickerService.get_all()
    return render(request, 'general/setup_settings.html', templatetags)
