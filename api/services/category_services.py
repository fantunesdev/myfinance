from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.models import Category
from statement.services import category_services


def get_categories(user):
    categories = category_services.get_categories(user)
    if categories:
        return categories
    raise Http404


def get_category_by_id(id, user):
    try:
        return category_services.get_category_by_id(id, user)
    except ObjectDoesNotExist:
        raise Http404


def get_categories_by_type(type, user):
    categories = Category.objects.filter(type=type, user=user)
    if categories:
        return categories
    raise Http404
