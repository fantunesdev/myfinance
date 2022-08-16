from django.http import Http404

from balanco.services import movimentacao_service
from statement.services import transaction_services


def get_transactions(user):
    transactions = transaction_services.get_transactions(user)
    if transactions:
        return transactions
    raise Http404


def get_transactions_by_year(year, user):
    transactions = transaction_services.get_transactions_by_year(year, user)
    if transactions:
        return transactions
    raise Http404


def get_transactions_by_year_and_month(year, month, user):
    transactions = transaction_services.get_transactions_by_year_and_month(year, month, user)
    if transactions:
        return transactions
    raise Http404
