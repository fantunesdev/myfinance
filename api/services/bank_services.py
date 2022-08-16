from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.services import bank_services


def get_bank_by_id(id):
    try:
        return bank_services.get_bank_by_id(id)
    except ObjectDoesNotExist:
        return Http404
