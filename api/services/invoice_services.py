from django.http import Http404

from balanco.services import fatura_service


def get_invoice_year_month(year, month, card, user):
    invoice = fatura_service.listar_fatura_ano_mes(year, month, card, user)
    if invoice:
        return invoice
    raise Http404
