"""
Este módulo fornece serviços relacionados às categorias do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.services.category_service import CategoryService


def get_categories(user):
    """
    Obtém todas as categorias associadas a um usuário.
    """
    categories = CategoryService.get_all()
    if categories:
        return categories
    raise Http404


def get_category_by_id(id, user):
    """
    Obtém uma categoria específica pelo seu ID e usuário associado.

    Parameters:
    - id: O ID da categoria a ser recuperada.
    """
    try:
        return CategoryService.get_by_id(id)
    except ObjectDoesNotExist as exception:
        raise ObjectDoesNotExist from exception


def get_categories_by_type(type, user):
    """
    Obtém todas as categorias de um determinado tipo associadas a um usuário.

    Parameters:
    - type: O tipo de categoria a ser recuperado. Valores possíves: entrada, saida.
    """
    categories = CategoryService.get_by_type(type)
    if categories:
        return categories
    raise Http404
