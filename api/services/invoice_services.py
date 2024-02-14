"""
Este módulo fornece serviços relacionados às faturas dos cartões do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.http import Http404

from statement.services import invoice_services


def get_invoice_by_year_and_month(card, year, month, user):
    """
    Obtém a fatura associada a um cartão para um ano e mês específicos.

    Parameters:
    - card: O ID do cartão para o qual a fatura será recuperada.
    - year: O ano para o qual a fatura será recuperada.
    - month: O mês para o qual a fatura será recuperada.
    - user: O usuário associado ao cartão.

    Returns:
    A fatura correspondente ao cartão, ano e mês fornecidos.

    Raises:
    Http404: Se nenhuma fatura for encontrada para o cartão, ano e mês fornecidos.
    """
    invoice = invoice_services.get_invoice_by_card_year_and_month(
        card, year, month, user
    )
    if invoice:
        return invoice
    raise Http404
