"""
Este módulo fornece serviços relacionados à configuração de visão do próximo mês do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.services import next_month_view_services


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
        return next_month_view_services.get_next_month_view_by_user(user)
    except ObjectDoesNotExist:
        raise Http404
