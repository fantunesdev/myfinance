from django.http import Http404

from balanco.services import movimentacao_service


def get_transactions(user):
    transactions = movimentacao_service.listar_movimentacoes(user)
    if transactions:
        return transactions
    raise Http404


def get_transactions_year(year, user):
    transactions = movimentacao_service.listar_movimentacoes_ano(year, user)
    if transactions:
        return transactions
    raise Http404


def get_transactions_year_month(year, month, user):
    transactions = movimentacao_service.listar_movimentacoes_ano_mes(year, month, user)
    if transactions:
        return transactions
    raise Http404
