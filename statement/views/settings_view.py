from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from statement.models import FixedIncomeSecurity
from statement.repositories.templatetags_repository import set_menu_templatetags, set_templatetags
from statement.services.index_services import IndexServices
from statement.services import (
    account_services,
    bank_services,
    card_services,
    category_services,
    fixed_expenses_services,
    flag_services,
    next_month_view_services,
    subcategory_services,
)


@login_required
def setup_settings(request):
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['accounts'] = account_services.get_accounts(request.user)
    templatetags['next_month_view'] = next_month_view_services.get_next_month_view_by_user(request.user)
    templatetags['banks'] = bank_services.get_banks()
    templatetags['flags'] = flag_services.get_flags()
    templatetags['cards'] = card_services.get_cards(request.user)
    templatetags['categories'] = category_services.get_categories(request.user)
    templatetags['fixed_expenses'] = fixed_expenses_services.get_fixed_expenses(request.user)
    templatetags['indexes'] = IndexServices.all()
    templatetags['subcategories'] = subcategory_services.get_subcategories(request.user)
    templatetags['fixed_income_securities'] = FixedIncomeSecurity.objects.all()
    
    return render(request, 'general/setup_settings.html', templatetags)
