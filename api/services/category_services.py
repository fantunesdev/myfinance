"""
Este módulo fornece serviços relacionados às categorias do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.models import Category
from statement.services import category_services


def get_categories(user):
    """
    Obtém todas as categorias associadas a um usuário.

    Parameters:
    - user: O usuário para o qual as categorias devem ser recuperadas.

    Returns:
    Uma lista de categorias associadas ao usuário fornecido.

    Raises:
    Http404: Se nenhuma conta estiver associada ao usuário.
    """
    categories = category_services.get_categories(user)
    if categories:
        return categories
    raise Http404


def get_category_by_id(id, user):
    """
    Obtém uma categoria específica pelo seu ID e usuário associado.

    Parameters:
    - id: O ID da categoria a ser recuperada.
    - user: O usuário associado à categoria.

    Returns:
    A categoria correspondente ao ID fornecido e usuário associado.

    Raises:
    Http404: Se a categoria não for encontrada com o ID e usuário fornecidos.
    """
    try:
        return category_services.get_category_by_id(id, user)
    except ObjectDoesNotExist:
        raise Http404


def get_categories_by_type(type, user):
    """
    Obtém todas as categorias de um determinado tipo associadas a um usuário.

    Parameters:
    - type: O tipo de categoria a ser recuperado. Valores possíves: entrada, saida.
    - user: O usuário associado às categorias.

    Returns:
    Uma lista de categorias do tipo especificado associadas ao usuário.

    Raises:
    Http404: Se nenhuma categoria for encontrada com o tipo e usuário fornecidos.
    """
    categories = Category.objects.filter(type=type, user=user)
    if categories:
        return categories
    raise Http404
