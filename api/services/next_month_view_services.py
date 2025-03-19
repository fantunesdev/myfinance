"""
Este módulo fornece serviços relacionados à configuração de visão do próximo mês do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.services.next_month_view import NextMonthViewService


def get_next_month_view(user):
    """
    Obtém as configurações de visualização do próximo mês associada a um usuário.

    Parameters:
    - user: O usuário para o qual a visualização do próximo mês será recuperada.

    Returns:
    As configurações da visualização do próximo mês associada ao usuário.

    Raises:
    Http404: Se nenhuma configuração de visualização do próximo mês for encontrada para o usuário.
    """
    try:
        return NextMonthViewService.get_all(user).first()
    except ObjectDoesNotExist:
        raise Http404
