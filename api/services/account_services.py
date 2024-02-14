"""
Este módulo fornece serviços relacionados às contas do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.services import account_services


def get_accounts(user):
    """
    Obtém todas as contas associadas a um usuário.

    Parameters:
    - user: O usuário para o qual as contas devem ser recuperadas.

    Returns:
    Uma lista de contas associadas ao usuário fornecido.

    Raises:
    Http404: Se nenhuma conta estiver associada ao usuário.
    """
    accounts = account_services.get_accounts(user)
    if accounts:
        return accounts
    else:
        return Http404


def get_account_by_id(id, user):
    """
    Obtém uma conta específica pelo seu ID e usuário associado.

    Parameters:
    - id: O ID da conta a ser recuperada.
    - user: O usuário associado à conta.

    Returns:
    A conta correspondente ao ID fornecido e usuário associado.

    Raises:
    Http404: Se a conta não for encontrada com o ID e usuário fornecidos.
    """
    try:
        return account_services.get_account_by_id(id, user)
    except ObjectDoesNotExist:
        return Http404
