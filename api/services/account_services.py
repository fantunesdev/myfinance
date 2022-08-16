from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.services import account_services


def get_accounts(user):
    accounts = account_services.get_accounts(user)
    if accounts:
        return accounts
    else:
        return Http404


def get_account_by_id(id, user):
    try:
        account_services.get_account_by_id(id, user)
    except ObjectDoesNotExist:
        return Http404
