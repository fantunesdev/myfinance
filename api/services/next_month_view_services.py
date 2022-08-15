from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from balanco.services import antecipation_service


def get_next_month_view(user):
    try:
        return antecipation_service.read_atecipation_user(user)
    except ObjectDoesNotExist:
        raise Http404
