from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.services import next_month_view_services


def get_next_month_view(user):
    try:
        return next_month_view_services.get_next_month_view_by_user(user)
    except ObjectDoesNotExist:
        raise Http404
