from django.http import Http404

from statement.services import extract_services


def get_extract_by_year_and_month(account_id, year, month, user):
    extract = extract_services.get_extract_by_account_year_and_month(account_id, year, month, user)
    if extract:
        return extract
    raise Http404