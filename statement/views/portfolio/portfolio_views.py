from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.services.portfolio.fixed_income_services import FixedIncomeService
from statement.repositories.templatetags_repository import set_menu_templatetags, set_templatetags


@login_required
def get_portfolio(request):
    total_fixed_income = FixedIncomeService.get_total_amount(request.user)
    total_variable_income = 0
    total_cryptocurrencies = 0
    total_amount = total_fixed_income + total_variable_income + total_cryptocurrencies
    templatetags = set_templatetags()
    templatetags['total_fixed_income'] = total_fixed_income
    templatetags['total_variable_income'] = total_variable_income
    templatetags['total_cryptocurrencies'] = total_cryptocurrencies
    templatetags['total_amount'] = total_amount
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'portfolio/get_portfolio.html', templatetags)
