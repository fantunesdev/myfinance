from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.entities.portion import Portion
from statement.forms.general_forms import ExclusionForm
from statement.forms.portion_form import PortionForm
from statement.repositories.templatetags_repository import set_menu_templatetags, set_templatetags
from statement.services import dream_services, portion_services


@login_required
def create_portion(request, id_dream):
    if request.method == 'POST':
        portion_form = PortionForm(request.POST)
        if portion_form.is_valid():
            dream = dream_services.list_dream_by_id(id_dream, request.user)
            new_portion = Portion(
                date=portion_form.cleaned_data['date'],
                value=portion_form.cleaned_data['value'],
                dream=dream,
                user=request.user,
            )
            portion_services.create_portion(new_portion)
            return redirect('list_dreams')
        else:
            print(portion_form.errors)
    else:
        portion_form = PortionForm()
        templatetags = set_templatetags()
        set_menu_templatetags(request.user, templatetags)
        templatetags['portion_form'] = portion_form
        return render(request, 'portion/portion_form.html', templatetags)


@login_required
def list_portions(request):
    portions = portion_services.list_portions(request.user)
    templatetags = set_templatetags()
    templatetags['portions'] = portions
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'portion/get_portions.html', templatetags)


@login_required
def update_portion(request, id_dream, id):
    dream = dream_services.list_dream_by_id(id_dream, request.user)
    old_portion = portion_services.list_portion_by_id(id, request.user)
    portion_form = PortionForm(request.POST or None, instance=old_portion)
    if portion_form.is_valid():
        new_portion = Portion(
            date=portion_form.cleaned_data['date'],
            value=portion_form.cleaned_data['value'],
            dream=dream,
            user=request.user,
        )
        portion_services.update_portion(old_portion, new_portion)
        return redirect('detail_dream', dream.id)
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['dream'] = dream
    templatetags['portion_form'] = portion_form
    templatetags['old_portion'] = old_portion
    return render(request, 'portion/portion_form.html', templatetags)


@login_required
def delete_portion(request, id_dream, id):
    portion = portion_services.list_portion_by_id(id, request.user)
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        portion_services.delete_portion(portion)
        return redirect('list_dreams')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['portion'] = portion
    templatetags['exclusion_form'] = exclusion_form
    return render(request, 'portion/exclusion_confirmation_portion.html', templatetags)
