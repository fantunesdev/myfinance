from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.forms.general_forms import ExclusionForm
from statement.forms.installment_form import (
    AdvanceInstallmentForm,
    InstallmentForm,
)
from statement.models import Transaction
from statement.repositories import installment_repository
from statement.repositories.templatetags_repository import *
from statement.repositories.transaction_repository import (
    calculate_total_revenue_expenses,
)
from statement.services import (
    installment_services,
    transaction_installment_services,
    transaction_services,
)


@login_required
def detail_installment(request, id):
    installment = installment_services.get_installment_by_id(id, request.user)
    transactions = (
        transaction_installment_services.get_transaction_by_installment(
            installment
        )
    )
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(
        transactions
    )
    templatetags = set_templatetags()
    set_dashboard_templatetags(
        templatetags, revenue, expenses, cards, cash, fixed
    )
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['installment'] = installment
    return render(request, 'installment/detail_installment.html', templatetags)


@login_required
def update_installment(request, id):
    installment = installment_services.get_installment_by_id(id, request.user)
    transactions = (
        transaction_installment_services.get_transaction_by_installment(
            installment
        )
    )
    installment_form = InstallmentForm(
        request.POST or None, instance=transactions[0]
    )
    if installment_form.is_valid():
        new_transaction = Transaction(
            release_date=installment_form.cleaned_data['release_date'],
            payment_date=None,
            account=installment_form.cleaned_data['account'],
            card=installment_form.cleaned_data['card'],
            category=installment_form.cleaned_data['category'],
            subcategory=installment_form.cleaned_data['subcategory'],
            description=installment_form.cleaned_data['description'],
            value=installment_form.cleaned_data['value'],
            installments_number=installment_form.cleaned_data[
                'installments_number'
            ],
            paid=0,
            fixed=installment_form.cleaned_data['fixed'],
            annual=installment_form.cleaned_data['annual'],
            currency=installment_form.cleaned_data['currency'],
            observation=installment_form.cleaned_data['observation'],
            remember=installment_form.cleaned_data['remember'],
            type=installment_form.cleaned_data['type'],
            effected=installment_form.cleaned_data['effected'],
            home_screen=installment_form.cleaned_data['home_screen'],
            user=request.user,
            installment=installment,
        )
        reorder_release_dates = installment_form.cleaned_data[
            'reorder_release_dates'
        ]
        installment_repository.update_installment(
            transactions, new_transaction, reorder_release_dates
        )
        return redirect('get_current_month_transactions')
    else:
        print(installment_form.errors)
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['installment'] = installment
    templatetags['installment_form'] = installment_form
    return render(request, 'installment/detail_installment.html', templatetags)


@login_required
def advance_installments(request, id):
    installment = installment_services.get_installment_by_id(id, request.user)
    installments = (
        transaction_installment_services.get_transaction_by_installment(
            installment
        )
    )
    if request.method == 'POST':
        installment_form = AdvanceInstallmentForm(request.POST)
        if installment_form.is_valid():
            quantity = installment_form.cleaned_data['quantity']
            initial_date = installment_form.cleaned_data['initial_date']
            installment_repository.advance_installments(
                quantity, initial_date, installments
            )
            return redirect('get_current_month_transactions')
        else:
            print(installment_form.errors)
    else:
        installment_form = AdvanceInstallmentForm()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['installments'] = installments
    templatetags['installment'] = installment
    templatetags['installment_form'] = installment_form
    return render(
        request, 'installment/advance_installments.html', templatetags
    )


@login_required
def delete_installment(request, id):
    installment = installment_services.get_installment_by_id(id, request.user)
    transactions = (
        transaction_installment_services.get_transaction_by_installment(
            installment
        )
    )
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        installment_services.delete_installment(installment)
        return redirect('get_current_month_transactions')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['exclusion_form'] = exclusion_form
    templatetags['installment'] = installment
    templatetags['transactions'] = transactions
    return render(request, 'installment/detail_installment.html', templatetags)


@login_required
def delete_parcel(request, id):
    transaction = transaction_services.get_transaction_by_id(id, request.user)
    transactions = (
        transaction_installment_services.get_transaction_by_installment(
            transaction.installment
        )
    )
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        transaction.installments_number -= 1
        installment_repository.update_installment(transactions, transaction)
        return redirect('get_current_month_transactions')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['exclusion_form'] = exclusion_form
    templatetags['transaction'] = transaction
    templatetags['transactions'] = transactions
    return render(request, 'transaction/detail_transaction.html', templatetags)
