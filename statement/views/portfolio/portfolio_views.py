from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.models import FixedIncome
from statement.repositories.templatetags_repository import set_menu_templatetags, set_templatetags


@login_required
def get_portfolio(request):
    fixed_income = FixedIncome.objects.all()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'portfolio/get_portfolio.html', templatetags)