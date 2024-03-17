from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from statement.forms.general_forms import NavigationForm
from statement.repositories.templatetags_repository import (
    set_menu_templatetags,
    set_templatetags,
)


@login_required
def show_dashboard(request):
    current_year = date.today().year
    templatetags = set_templatetags()
    templatetags['navigation_form'] = NavigationForm(
        initial={'year': current_year}
    )
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'dashboards/index.html', templatetags)
