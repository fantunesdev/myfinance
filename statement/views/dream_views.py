from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.entities.dream import Dream
from statement.forms.dream_form import DreamForm
from statement.forms.general_forms import ExclusionForm
from statement.repositories.templatetags_repository import (
    set_menu_templatetags,
    set_templatetags,
)
from statement.services import dream_services
from statement.services import portion_services


@login_required
def create_dream(request):
    if request.method == 'POST':
        dream_form = DreamForm(request.POST)
        if dream_form.is_valid():
            new_dream = Dream(
                description=dream_form.cleaned_data['description'],
                value=dream_form.cleaned_data['value'],
                limit_date=dream_form.cleaned_data['limit_date'],
                user=request.user,
            )
            dream_services.create_dream(new_dream)
            return redirect('list_dreams')
        else:
            print(dream_form.errors)
    else:
        dream_form = DreamForm()
        templatetags = set_templatetags()
        set_menu_templatetags(request.user, templatetags)
        templatetags['dream_form'] = dream_form
        return render(request, 'dream/dream_form.html', templatetags)


@login_required
def list_dreams(request):
    dreams = dream_services.list_dreams(request.user)
    templatetags = set_templatetags()
    templatetags['dreams'] = dreams
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'dream/get_dreams.html', templatetags)


@login_required
def detail_dream(request, id):
    dream = dream_services.list_dream_by_id(id, request.user)
    portions = portion_services.list_portions_by_dream(dream, request.user)
    templatetags = set_templatetags()
    templatetags['dream'] = dream
    templatetags['portions'] = portions
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'dream/exclusion_confirmation_dream.html', templatetags)


@login_required
def update_dream(request, id):
    old_dream = dream_services.list_dream_by_id(id, request.user)
    dream_form = DreamForm(request.POST or None, instance=old_dream)
    if dream_form.is_valid():
        new_dream = Dream(
            description=dream_form.cleaned_data['description'],
            value=dream_form.cleaned_data['value'],
            limit_date=dream_form.cleaned_data['limit_date'],
            user=request.user,
        )
        dream_services.update_dream(old_dream, new_dream)
        return redirect('list_dreams')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['dream_form'] = dream_form
    templatetags['old_dream'] = old_dream
    templatetags['portions'] = portion_services.list_portions_by_dream(old_dream, request.user)
    return render(request, 'dream/dream_form.html', templatetags)



@login_required
def delete_dream(request, id):
    dream = dream_services.list_dream_by_id(id, request.user)
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        dream_services.delete_dream(dream)
        return redirect('list_dreams')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['dream'] = dream
    templatetags['exclusion_form'] = exclusion_form
    return render(
        request, 'dream/exclusion_confirmation_dream.html', templatetags
    )