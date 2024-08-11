from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.entities.bank import Bank
from statement.forms.bank_form import BankForm
from statement.forms.general_forms import ExclusionForm
from statement.repositories.templatetags_repository import set_menu_templatetags, set_templatetags
from statement.services import bank_services


@login_required
def create_bank(request):
    if request.method == 'POST':
        bank_form = BankForm(request.POST, request.FILES)
        if bank_form.is_valid():
            banco = Bank(
                description=bank_form.cleaned_data['description'],
                code=bank_form.cleaned_data['code'],
                icon=bank_form.cleaned_data['icon'],
            )
            bank_services.create_bank(banco)
            return redirect('setup_settings')
    else:
        bank_form = BankForm()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['bank_form'] = bank_form
    return render(request, 'bank/bank_form.html', templatetags)


@login_required
def get_banks(request):
    banks = bank_services.get_banks()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['banks'] = banks
    return render(request, 'banco/listar.html', templatetags)


@login_required
def update_bank(request, id):
    old_bank = bank_services.get_bank_by_id(id)
    bank_form = BankForm(request.POST or None, request.FILES or None, instance=old_bank)
    if bank_form.is_valid():
        new_bank = Bank(
            description=bank_form.cleaned_data['description'],
            code=bank_form.cleaned_data['code'],
            icon=bank_form.cleaned_data['icon'],
        )
        bank_services.update_bank(old_bank, new_bank)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['bank_form'] = bank_form
    templatetags['old_bank'] = old_bank
    return render(request, 'bank/bank_form.html', templatetags)


@login_required
def delete_bank(request, id):
    bank = bank_services.get_bank_by_id(id)
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        bank_services.delete_bank(bank)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['bank'] = bank
    templatetags['exclusion_form'] = exclusion_form
    return render(request, 'bank/exclusion_confirmation_bank.html', templatetags)
