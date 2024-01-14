from django.http import Http404

from statement.models import Subcategory
from statement.services import subcategory_services


def get_subcategories(user):
    subcategories = subcategory_services.get_subcategories(user)
    if subcategories:
        return subcategories
    raise Http404


def get_subcategories_by_category(category_id, user):
    subcategories = Subcategory.objects.select_related('category').filter(
        category=category_id, user=user
    )
    if subcategories:
        return subcategories
    raise Http404
