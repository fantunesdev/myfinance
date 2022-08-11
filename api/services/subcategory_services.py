from django.http import Http404

from balanco.models import Subcategoria


def get_subcategories(user):
    subcategories = Subcategoria.objects.filter(usuario=user)
    if subcategories:
        return subcategories
    raise Http404


def get_subcategories_category(category_id, user):
    subcategories = Subcategoria.objects.select_related('categoria').filter(categoria=category_id, usuario=user)
    if subcategories:
        return subcategories
    raise Http404
