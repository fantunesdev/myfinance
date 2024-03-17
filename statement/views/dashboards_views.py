from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..repositories.templatetags_repository import (
    set_menu_templatetags,
    set_templatetags,
)


@login_required
def show_dashboard(request):
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'dashboards/index.html', templatetags)
