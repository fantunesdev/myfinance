import pprint
from datetime import date

from dateutil.relativedelta import relativedelta

from statement.entities.installment import Installment
from statement.forms.transaction_forms import *
from statement.services import (
    account_services,
    fixed_expenses_services,
    installment_services,
    transaction_services,
)


def validate_form_by_type(type, *args):
    if type == 'entrada':
        return TransactionRevenueForm(*args)
    return TransactionExpenseForm(*args)


def validate_account_balance(transaction):
    if transaction.account:
        if transaction.type == 'entrada':
            deposit(transaction.account, transaction.value)
        else:
            withdraw(transaction.account, transaction.value)


def validate_account_balance_when_delete_transaction(transaction):
    if transaction.account:
        if transaction.type == 'entrada':
            withdraw(transaction.account, transaction.value)
        else:
            deposit(transaction.account, transaction.value)


def validate_new_account_balance(
    old_transaction, new_transaction, old_transaction_copy
):
    if new_transaction.account:
        if old_transaction.type == 'entrada':
            withdraw(old_transaction_copy.account, old_transaction_copy.value)
            if old_transaction_copy.account == new_transaction.account:
                new_transaction.account.balance = (
                    old_transaction_copy.account.balance
                )
            deposit(new_transaction.account, new_transaction.value)
        else:
            if old_transaction_copy.card:
                account = account_services.get_account_by_id(
                    new_transaction.account.id, new_transaction.user
                )
                old_transaction_copy.account = account
            deposit(old_transaction_copy.account, old_transaction_copy.value)
            if old_transaction_copy.account == new_transaction.account:
                new_transaction.account.balance = (
                    old_transaction_copy.account.balance
                )
            withdraw(new_transaction.account, new_transaction.value)


def withdraw(account, value):
    account_services.withdraw(account, value)


def deposit(account, value):
    account_services.deposit(account, value)


def validate_installment(transaction):
    if transaction.installments_number > 0:
        piecemeal(transaction)
    else:
        transaction_services.create_transaction(transaction)


def piecemeal(transaction):
    installment = Installment(
        release_date=transaction.release_date,
        description=transaction.description,
        user=transaction.user,
    )
    installment_db = installment_services.create_installment(installment)
    transaction.installment = installment_db
    for i in range(0, transaction.installments_number):
        transaction.payment_date = add_month(transaction, i)
        transaction.paid += 1
        transaction.installment = installment_db
        transaction_services.create_transaction(transaction)


def add_month(transaction, repetition):
    if transaction.card:
        transaction.payment_date = date(
            transaction.release_date.year,
            transaction.release_date.month,
            transaction.card.expiration_day,
        )
        if transaction.release_date.day >= transaction.card.closing_day:
            transaction.payment_date += relativedelta(months=1)
        transaction.payment_date += relativedelta(months=repetition)
    else:
        if repetition == 0:
            transaction.payment_date += relativedelta(months=0)
        else:
            transaction.payment_date += relativedelta(months=1)
    return transaction.payment_date


def calculate_total_revenue_expenses(transactions):
    revenue = 0
    expenses = 0
    cards = 0
    cash = 0
    fixed = 0
    for transaction in transactions:
        if transaction.type == 'saida':
            if not transaction.category.ignore:
                if transaction.card:
                    cards += transaction.value
                else:
                    cash += transaction.value
                if transaction.fixed:
                    fixed += transaction.value
                expenses += transaction.value
        else:
            revenue += transaction.value
    if transactions:
        fixed_expenses = fixed_expenses_services.get_fixed_expenses(
            transactions[0].user
        )
        for fixed_expense in fixed_expenses:
            fixed += fixed_expense.value
    return revenue, expenses, cards, cash, fixed
