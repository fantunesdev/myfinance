from django.http import Http404

from statement.services import invoice_services


def get_invoice_by_year_and_month(card, year, month, user):
    invoice = invoice_services.get_invoice_by_card_year_and_month(
        card, year, month, user
    )
    if invoice:
        return invoice
    raise Http404
