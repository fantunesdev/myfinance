"""
Este módulo fornece serviços relacionados aos lançamentos do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.http import Http404

from statement.services import transaction_services


def get_transactions(user):
    """
    Obtém todos os lançamentos associadas a um usuário.

    Parameters:
    - user: O usuário para o qual os lançamentos devem ser recuperadas.

    Returns:
    Uma lista de lançamentos associadas ao usuário fornecido.

    Raises:
    Http404: Se nenhuma conta estiver associada ao usuário.
    """
    transactions = transaction_services.get_transactions(user)
    if transactions:
        return transactions
    raise Http404


def get_transactions_by_year(year, user):
    """
    Obtém todas os lançamentos associadas a um ano específico de um usuário.

    Parameters:
    - year: O ano para o qual os lançamentos serão recuperadas.
    - user: O usuário associado aos lançamentos.

    Returns:
    Uma lista de lançamentos associadas ao ano e usuário fornecidos.

    Raises:
    Http404: Se nenhum lançamento for encontrado para o ano e usuário fornecidos.
    """
    transactions = transaction_services.get_transactions_by_year(year, user)
    if transactions:
        return transactions
    raise Http404


def get_transactions_by_year_and_month(year, month, user):
    """
    Obtém todos os lançamentos associados a um ano e mês específicos de um usuário.

    Parameters:
    - year: O ano para o qual os lançamentos serão recuperados.
    - month: O mês para o qual os lançamentos serão recuperados.
    - user: O usuário associado aos lançamentos.

    Returns:
    Uma lista de lançamentos associados ao ano, mês e usuário fornecidos.

    Raises:
    Http404: Se nenhum lançamento for encontrado para o ano, mês e usuário fornecidos.
    """
    transactions = transaction_services.get_transactions_by_year_and_month(year, month, user)
    if transactions:
        return transactions
    raise Http404
