"""
Este módulo fornece serviços relacionados aos bancos do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.services.core.bank import BankService


def get_banks():
    """
    Obtém todos os bancos associadas a um usuário.

    Parameters:
    - user: O usuário para o qual os bancos devem ser recuperadas.

    Returns:
    Uma lista de bancos associadas ao usuário fornecido.

    Raises:
    Http404: Se nenhum banco estiver associado ao usuário.
    """
    banks = BankService.get_all()
    if banks:
        return banks
    return Http404


def get_banks_by_account(account_id):
    pass


def get_bank_by_id(id):
    """
    Obtém um banco específica pelo seu ID e usuário associado.

    Parameters:
    - id: O ID do banco a ser recuperado.
    - user: O usuário associado ao banco.

    Returns:
    O banco correspondente ao ID fornecido e usuário associado.

    Raises:
    Http404: Se o banco não for encontrado com o ID e usuário fornecidos.
    """
    try:
        return BankService.get_by_id(id)
    except ObjectDoesNotExist:
        return Http404
