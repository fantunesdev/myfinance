from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from balanco.models import Categoria


def get_categories(user):
    categories = Categoria.objects.filter(usuario=user)
    if categories:
        return categories
    raise Http404


def get_category_id(id, user):
    try:
        return Categoria.objects.get(id=id, usuario=user)
    except ObjectDoesNotExist:
        raise Http404


def get_category_type(type, user):
    categories = Categoria.objects.filter(tipo=type, usuario=user)
    if categories:
        return categories
    raise Http404
