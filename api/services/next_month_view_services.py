"""
Este módulo fornece serviços relacionados à configuração de visão do próximo mês do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.http import Http404

from statement.services.next_month_view import NextMonthViewService


def get_next_month_view(user):
    """Retorna a configuração de next month do `Profile` do usuário ou lança 404."""
    nm = NextMonthViewService.get(user)
    if nm is None:
        raise Http404
    return nm
