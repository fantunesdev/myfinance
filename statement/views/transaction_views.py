import copy

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from datetime import datetime

from statement.entities.transaction import Transaction
from statement.forms.general_forms import ExclusionForm
from statement.repositories import next_month_view_repository, installment_repository
from statement.repositories.templatetags_repository import set_menu_templatetags, set_dashboard_templatetags, \
    set_templatetags, set_transaction_navigation_templatetags
from statement.repositories.transaction_repository import *
from statement.services import transaction_installment_services


@login_required
def create_transaction(request, type):
    if request.method == 'POST':
        transaction_form = TransactionForm(request.POST)
        if transaction_form.is_valid():
            transaction = Transaction(
                release_date=transaction_form.cleaned_data['release_date'],
                payment_date=transaction_form.cleaned_data['payment_date'],
                account=transaction_form.cleaned_data['account'],
                card=transaction_form.cleaned_data['card'],
                category=transaction_form.cleaned_data['category'],
                subcategory=transaction_form.cleaned_data['subcategory'],
                description=transaction_form.cleaned_data['description'],
                value=transaction_form.cleaned_data['value'],
                installments_number=transaction_form.cleaned_data['installments_number'],
                paid=transaction_form.cleaned_data['paid'],
                fixed=transaction_form.cleaned_data['fixed'],
                annual=transaction_form.cleaned_data['annual'],
                currency=transaction_form.cleaned_data['currency'],
                observation=transaction_form.cleaned_data['observation'],
                remember=transaction_form.cleaned_data['remember'],
                type=type,
                effected=transaction_form.cleaned_data['effected'],
                home_screen=transaction_form.cleaned_data['home_screen'],
                user=request.user,
                installment=None
            )
            home_screen = transaction.account.home_screen if transaction.account else transaction.card.home_screen
            transaction.home_screen = home_screen
            validate_account_balance(transaction)
            validate_installment(transaction)
            return redirect('get_current_month_transactions')
        else:
            print(transaction_form.errors)
            return transaction_form.errors
    else:
        transaction_form = validate_form_by_type(type, request.user)
        print(request)
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['transaction_form'] = transaction_form
    templatetags['type'] = type
    return render(request, 'transaction/transaction_form.html', templatetags)


@login_required
def get_transactions(request):
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transaction_services.get_transactions(request.user)
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_transactions_by_description(request, description):
    year = datetime.today().year
    month = datetime.today().month
    transactions = transaction_services.get_transactions_by_description(description, request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, year, month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_transactions_by_year(request, year):
    transactions = transaction_services.get_transactions_by_year(year, request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, year)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_current_month_transactions(request):
    current_month = next_month_view_repository.get_current_month(request.user)
    transactions = transaction_services.get_transactions_by_year_and_month(year=current_month.year,
                                                                           month=current_month.month,
                                                                           user=request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, current_month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_transactions_by_year_and_month(request, year, month):
    transactions = transaction_services.get_transactions_by_year_and_month(year, month, request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, year, month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_fixed_transactions_by_year_and_month(request, year, month):
    transactions = transaction_services.get_fixed_transactions_by_year_and_month(year, month, request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, year, month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def detail_transaction(request, id):
    transaction = transaction_services.get_transaction_by_id(id, request.user)
    templatetags = set_templatetags()
    if transaction.installment:
        transactions = transaction_installment_services.get_transaction_by_installment(transaction.parcelamento)
        templatetags['transactions'] = transactions
    templatetags['transaction'] = transaction
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'transaction/detail_transaction.html', templatetags)


@login_required
def update_transaction(request, id):
    old_transaction = transaction_services.get_transaction_by_id(id, request.user)
    transaction_form = UpdateTransactionForm(request.POST or None, instance=old_transaction)
    old_transaction_copy = copy.deepcopy(old_transaction)
    if transaction_form.is_valid():
        new_transaction = Transaction(
            release_date=transaction_form.cleaned_data['release_date'],
            payment_date=transaction_form.cleaned_data['payment_date'],
            account=transaction_form.cleaned_data['account'],
            card=transaction_form.cleaned_data['card'],
            category=transaction_form.cleaned_data['category'],
            subcategory=transaction_form.cleaned_data['subcategory'],
            description=transaction_form.cleaned_data['description'],
            value=transaction_form.cleaned_data['value'],
            installments_number=old_transaction.installments_number,
            paid=old_transaction.paid,
            fixed=transaction_form.cleaned_data['fixed'],
            annual=transaction_form.cleaned_data['annual'],
            currency=transaction_form.cleaned_data['currency'],
            observation=transaction_form.cleaned_data['observation'],
            remember=transaction_form.cleaned_data['remember'],
            type=transaction_form.cleaned_data['type'],
            effected=transaction_form.cleaned_data['effected'],
            home_screen=transaction_form.cleaned_data['home_screen'],
            user=request.user,
            installment=old_transaction.installment
        )
        home_screen = new_transaction.account.home_screen if new_transaction.account else new_transaction.card.home_screen
        new_transaction.home_screen = home_screen
        validate_new_account_balance(old_transaction, new_transaction, old_transaction_copy)
        if transaction_form.cleaned_data['installment_option'] == 'parcelar':
            installment_repository.validate_installment(old_transaction_copy, new_transaction)
            return redirect('get_current_month_transactions')
        else:
            transaction_services.update_transaction(old_transaction, new_transaction)
        return redirect('get_current_month_transactions')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['transaction_form'] = transaction_form
    templatetags['old_transaction'] = old_transaction
    return render(request, 'transaction/transaction_form.html', templatetags)


@login_required
def delete_transaction(request, id):
    transaction = transaction_services.get_transaction_by_id(id, request.user)
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        transaction_services.delete_transaction(transaction)
        validate_account_balance_when_delete_transaction(transaction)
        return redirect('get_current_month_transactions')
    templatetags = set_templatetags()
    templatetags['exclusion_form'] = exclusion_form
    templatetags['transaction'] = transaction
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'transaction/detail_transaction.html', templatetags)
