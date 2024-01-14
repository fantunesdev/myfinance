from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from statement.forms.general_forms import NavigationForm
from statement.repositories.templatetags_repository import *
from statement.repositories.transaction_repository import (
    calculate_total_revenue_expenses,
)
from statement.services import extract_services, invoice_services


@login_required
def get_invoice_by_account(request, card_id):
    templatetags = set_templatetags()
    templatetags['transactions'] = invoice_services.get_extract_by_account(
        card_id, request.user
    )
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_invoice_by_account_and_year(request, card_id, year):
    transactions = extract_services.get_extract_by_account_and_year(
        card_id, year, request.user
    )
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(
        transactions
    )
    templatetags = set_templatetags()
    set_dashboard_templatetags(
        templatetags, revenue, expenses, cards, cash, fixed
    )
    set_transaction_navigation_templatetags(templatetags, year)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_current_month_invoice_by_card(request, card_id):
    current_month = date.today()
    transactions = invoice_services.get_invoice_by_card_year_and_month(
        card_id, current_month.year, current_month.month, request.user
    )
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(
        transactions
    )
    templatetags = set_templatetags()
    set_dashboard_templatetags(
        templatetags, revenue, expenses, cards, cash, fixed
    )
    set_transaction_navigation_templatetags(templatetags, current_month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['navigation_form'] = NavigationForm(
        initial={'year': current_month.year, 'month': current_month.month}
    )
    templatetags['card'] = card_services.get_card_by_id(card_id, request.user)
    return render(request, 'transaction/get_transactions.html', templatetags)


@login_required
def get_invoice_by_card_year_and_month(request, card_id, year, month):
    transactions = invoice_services.get_invoice_by_card_year_and_month(
        card_id, year, month, request.user
    )
    revenue, expenses, cards, cash, fixed = calculate_total_revenue_expenses(
        transactions
    )
    templatetags = set_templatetags()
    set_dashboard_templatetags(
        templatetags, revenue, expenses, cards, cash, fixed
    )
    set_transaction_navigation_templatetags(templatetags, year, month)
    set_menu_templatetags(request.user, templatetags)
    templatetags['transactions'] = transactions
    templatetags['navigation_form'] = NavigationForm(
        initial={'year': year, 'month': month}
    )
    templatetags['card'] = account_services.get_account_by_id(
        card_id, request.user
    )
    return render(request, 'transaction/get_transactions.html', templatetags)
