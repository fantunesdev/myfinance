from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from statement.entities.account import Account
from statement.forms.account_form import AccountForm
from statement.forms.general_forms import ExclusionForm
from statement.repositories import account_repository
from statement.repositories.templatetags_repository import set_templatetags, set_menu_templatetags
from statement.services import account_services


@login_required
def create_account(request):
    if request.method == 'POST':
        account_form = AccountForm(request.POST)
        if account_form.is_valid():
            account = Account(
                bank=account_form.cleaned_data['bank'],
                branch=account_form.cleaned_data['branch'],
                number=account_form.cleaned_data['number'],
                balance=account_form.cleaned_data['balance'],
                limits=account_form.cleaned_data['limits'],
                type=account_form.cleaned_data['type'],
                home_screen=account_form.cleaned_data['home_screen'],
                user=request.user
            )
            account_services.create_account(account)
            return redirect('setup_settings')
    else:
        account_form = AccountForm()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['account_form'] = account_form
    templatetags['accounts'] = account_services.get_accounts(request.user)
    return render(request, 'account/account_form.html', templatetags)


@login_required
def update_account(request, id):
    old_account = account_services.get_account_by_id(id, request.user)
    account_form = AccountForm(request.POST or None, instance=old_account)
    if account_form.is_valid():
        new_account = Account(
            bank=account_form.cleaned_data['bank'],
            branch=account_form.cleaned_data['branch'],
            number=account_form.cleaned_data['number'],
            balance=account_form.cleaned_data['balance'],
            limits=account_form.cleaned_data['limits'],
            type=account_form.cleaned_data['type'],
            home_screen=account_form.cleaned_data['home_screen'],
            user=request.user
        )
        account_repository.set_home_screen(old_account.id, new_account.home_screen, request.user)
        account_services.update_account(old_account, new_account)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['account_form'] = account_form
    templatetags['old_account'] = old_account
    return render(request, 'account/account_form.html', templatetags)


@login_required
def delete_account(request, id):
    account = account_services.get_account_by_id(id, request.user)
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        account_services.delete_account(account)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['exclusion_form'] = exclusion_form
    templatetags['account'] = account
    return render(request, 'account/exclusion_confirmation_account.html', templatetags)
