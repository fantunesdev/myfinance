from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from statement.forms.general_forms import NavigationForm
from statement.repositories.templatetags_repository import *
from statement.repositories.transaction_repository import calculate_total_revenue_expenses
from statement.services import extract_services


@login_required
def get_extract_by_account(request, account_id):
    templatetags = set_templatetags()
    templatetags['transactions'] = extract_services.get_extract_by_account(account_id, request.user)
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_extract_by_account_and_year(request, account_id, year):
    transactions = extract_services.get_extract_by_account_and_year(account_id, year, request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions, year, 1)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, year)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_current_month_extract_by_account(request, account_id):
    current_month = date.today()
    month = current_month.month
    year = current_month.year
    transactions = extract_services.get_extract_by_account_year_and_month(account_id, year, month, request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions, year, month)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, current_month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['navigation_form'] = NavigationForm(initial={'year': current_month.year, 'month': current_month.month})
    templatetags['account'] = account_services.get_account_by_id(account_id, request.user)
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_extract_by_account_year_and_month(request, account_id, year, month):
    transactions = extract_services.get_extract_by_account_year_and_month(account_id, year, month, request.user)
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(transactions, year, month)
    templatetags = set_templatetags()
    set_dashboard_templatetags(templatetags, revenue, expenses, cards, cash, fixed)
    set_transaction_navigation_templatetags(templatetags, year, month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['navigation_form'] = NavigationForm(initial={'year': year, 'month': month})
    templatetags['account'] = account_services.get_account_by_id(account_id, request.user)
    return render(request, 'transaction/get_transactions.html', templatetags)
