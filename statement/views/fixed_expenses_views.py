from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.entities.fixed_expense import FixedExpense
from statement.forms.fixed_expense_form import FixedExpensesForm
from statement.forms.general_forms import ExclusionForm
from statement.repositories.templatetags_repository import set_menu_templatetags, set_templatetags
from statement.services import fixed_expenses_services


@login_required
def create_fixed_expense(request):
    if request.method == 'POST':
        fixed_expenses_form = FixedExpensesForm(request.POST)
        if fixed_expenses_form.is_valid():
            new_fixed_expense = FixedExpense(
                start_date=fixed_expenses_form.cleaned_data['start_date'],
                end_date=fixed_expenses_form.cleaned_data['end_date'],
                description=fixed_expenses_form.cleaned_data['description'],
                value=fixed_expenses_form.cleaned_data['value'],
                user=request.user,
            )
            fixed_expenses_services.create_fixed_expense(new_fixed_expense)
            return redirect('setup_settings')
        else:
            print(fixed_expenses_form.errors)
    else:
        fixed_expenses_form = FixedExpensesForm()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['fixed_expenses_form'] = fixed_expenses_form
    return render(request, 'fixed_expenses/fixed_expenses_form.html', templatetags)


@login_required
def update_fixed_expense(request, id):
    old_fixed_expense = fixed_expenses_services.get_fixed_expense_by_id(id, request.user)
    fixed_expenses_form = FixedExpensesForm(request.POST or None, instance=old_fixed_expense)
    if fixed_expenses_form.is_valid():
        new_fixed_expense = FixedExpense(
            start_date=fixed_expenses_form.cleaned_data['start_date'],
            end_date=fixed_expenses_form.cleaned_data['end_date'],
            description=fixed_expenses_form.cleaned_data['description'],
            value=fixed_expenses_form.cleaned_data['value'],
            user=request.user,
        )
        fixed_expenses_services.update_fixed_expense(old_fixed_expense, new_fixed_expense)
        return redirect('setup_settings')
    else:
        print(fixed_expenses_form.errors)
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['fixed_expenses_form'] = fixed_expenses_form
    templatetags['old_fixed_expense'] = old_fixed_expense
    return render(request, 'fixed_expenses/fixed_expenses_form.html', templatetags)


@login_required
def delete_fixed_expense(request, id):
    fixed_expense = fixed_expenses_services.get_fixed_expense_by_id(id, request.user)
    if request.method == 'POST':
        fixed_expenses_services.delete_fixed_expense(fixed_expense)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['fixed_expense'] = fixed_expense
    templatetags['exclusion_form'] = ExclusionForm()
    return render(
        request,
        'fixed_expenses/exclusion_confirmation_fixed_expense.html',
        templatetags,
    )
