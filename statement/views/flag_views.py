from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.forms.flag_form import FlagForm
from statement.forms.general_forms import ExclusionForm
from statement.models import Flag
from statement.repositories.templatetags_repository import (
    set_menu_templatetags,
    set_templatetags,
)
from statement.services import flag_services


@login_required
def create_flag(request):
    if request.method == 'POST':
        flag_form = FlagForm(request.POST, request.FILES)
        if flag_form.is_valid():
            flag = Flag(
                description=flag_form.cleaned_data['description'],
                icon=flag_form.cleaned_data['icon'],
            )
            flag_services.create_flag(flag)
            return redirect('setup_settings')
    else:
        flag_form = FlagForm()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['flag_form'] = flag_form
    return render(request, 'flag/flag_form.html', templatetags)


@login_required
def update_flag(request, id):
    old_flag = flag_services.get_flag_by_id(id)
    flag_form = FlagForm(
        request.POST or None, request.FILES or None, instance=old_flag
    )
    if flag_form.is_valid():
        bandeira_nova = Flag(
            description=flag_form.cleaned_data['description'],
            icon=flag_form.cleaned_data['icon'],
        )
        flag_services.update_flag(old_flag, bandeira_nova)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['flag_form'] = flag_form
    templatetags['old_flag'] = old_flag
    return render(request, 'flag/flag_form.html', templatetags)


@login_required
def delete_flag(request, id):
    flag = flag_services.get_flag_by_id(id)
    if request.method == 'POST':
        flag_services.delete_flag(flag)
        return redirect('setup_settings')
    exclusion_form = ExclusionForm()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['exclusion_form'] = exclusion_form
    templatetags['flag'] = flag
    return render(
        request, 'flag/exclusion_confirmation_flag.html', templatetags
    )
