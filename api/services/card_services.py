"""
Este módulo fornece serviços relacionados aos cartões do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.services.core.card import CardService


def get_cards(user):
    """
    Obtém todos os cartões associadas a um usuário.

    Parameters:
    - user: O usuário para o qual os cartões devem ser recuperadas.

    Returns:
    Uma lista de cartões associadas ao usuário fornecido.

    Raises:
    Http404: Se nenhum cartão estiver associado ao usuário.
    """
    cards = CardService.get_all(user)
    if cards:
        return cards
    raise Http404


def get_card_by_id(card_id, user):
    """
    Obtém um cartão específica pelo seu ID e usuário associado.

    Parameters:
    - id: O ID do cartão a ser recuperado.
    - user: O usuário associado ao cartão.

    Returns:
    O cartão correspondente ao ID fornecido e usuário associado.

    Raises:
    Http404: Se o cartão não for encontrado com o ID e usuário fornecidos.
    """
    try:
        return CardService.get_by_id(card_id, user)
    except ObjectDoesNotExist:
        raise Http404
