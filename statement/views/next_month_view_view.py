from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.entities.next_month_view import NextMonthView
from statement.forms import next_month_view_form
from statement.repositories.templatetags_repository import (
    set_menu_templatetags,
    set_templatetags,
)
from statement.services import next_month_view_services


@login_required
def update_next_month_view(request):
    old_next_month_view = next_month_view_services.get_next_month_view_by_user(
        request.user
    )
    form_next_month_view = next_month_view_form.NextMonthViewForm(
        request.POST or None, instance=old_next_month_view
    )
    if form_next_month_view.is_valid():
        new_next_month_view = NextMonthView(
            day=form_next_month_view.cleaned_data['day'],
            active=form_next_month_view.cleaned_data['active'],
            user=request.user,
        )
        next_month_view_services.update_next_month_view(
            old_next_month_view, new_next_month_view
        )
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['old_next_month_view'] = old_next_month_view
    templatetags['form_next_month_view'] = form_next_month_view
    return render(
        request, 'next_month_view/form_next_month_view.html', templatetags
    )
