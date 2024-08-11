"""
Este módulo fornece serviços relacionados às subcategorias do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.http import Http404

from statement.models import Subcategory
from statement.services import subcategory_services


def get_subcategories(user):
    """
    Obtém todas as subcategorias associadas a um usuário.

    Parameters:
    - user: O usuário para o qual as subcategorias devem ser recuperadas.

    Returns:
    Uma lista de subcategorias associadas ao usuário fornecido.

    Raises:
    Http404: Se nenhuma conta estiver associada ao usuário.
    """
    subcategories = subcategory_services.get_subcategories(user)
    if subcategories:
        return subcategories
    raise Http404


def get_subcategories_by_category(category_id, user):
    """
    Obtém todas as subcategorias associadas a uma categoria específica de um usuário.

    Parameters:
    - category_id: O ID da categoria para a qual as subcategorias serão recuperadas.
    - user: O usuário associado às subcategorias.

    Returns:
    Uma lista de subcategorias associadas à categoria e usuário fornecidos.

    Raises:
    Http404: Se nenhuma subcategoria for encontrada para a categoria e usuário fornecidos.
    """
    subcategories = Subcategory.objects.select_related('category').filter(category=category_id, user=user)
    if subcategories:
        return subcategories
    raise Http404
