from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.entities.subcategory import Subcategory
from statement.forms.general_forms import ExclusionForm
from statement.forms.subcategory_form import SubcategoryForm
from statement.repositories.templatetags_repository import set_templatetags
from statement.services import (
    account_services,
    card_services,
    subcategory_services,
)


@login_required
def create_subcategory(request):
    if request.method == 'POST':
        subcategory_form = SubcategoryForm(request.POST)
        if subcategory_form.is_valid():
            subcategory = Subcategory(
                description=subcategory_form.cleaned_data['description'],
                category=subcategory_form.cleaned_data['category'],
                user=request.user,
            )
            subcategory_services.create_subcategory(subcategory)
            return redirect('setup_settings')
    else:
        subcategory_form = SubcategoryForm()
    templatetags = set_templatetags()
    templatetags['subcategoria_antiga'] = None
    templatetags['subcategory_form'] = subcategory_form
    templatetags['accounts'] = account_services.get_accounts(request.user)
    templatetags['cards'] = card_services.get_cards(request.user)
    return render(request, 'subcategory/subcategory_form.html', templatetags)


@login_required
def update_subcategory(request, id):
    old_subcategory = subcategory_services.get_subcategory_by_id(
        id, request.user
    )
    subcategory_form = SubcategoryForm(
        request.POST or None, instance=old_subcategory
    )
    if subcategory_form.is_valid():
        new_subcategory = Subcategory(
            description=subcategory_form.cleaned_data['description'],
            category=subcategory_form.cleaned_data['category'],
            user=request.user,
        )
        subcategory_services.update_subcategory(
            old_subcategory, new_subcategory
        )
        return redirect('setup_settings')
    templatetags = set_templatetags()
    templatetags['old_subcategory'] = old_subcategory
    templatetags['subcategory_form'] = subcategory_form
    templatetags['accounts'] = account_services.get_accounts(request.user)
    templatetags['cards'] = card_services.get_cards(request.user)
    return render(request, 'subcategory/subcategory_form.html', templatetags)


@login_required
def delete_subcategory(request, id):
    subcategory = subcategory_services.get_subcategory_by_id(id, request.user)
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        subcategory_services.delete_subcategory(subcategory)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    templatetags['subcategory'] = subcategory
    templatetags['exclusion_form'] = exclusion_form
    templatetags['accounts'] = account_services.get_accounts(request.user)
    templatetags['cards'] = card_services.get_cards(request.user)
    return render(
        request,
        'subcategory/exclusion_confirmation_subcategory.html',
        templatetags,
    )
