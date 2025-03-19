"""
Este módulo fornece serviços relacionados às faturas dos cartões do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.http import Http404

from statement.services.core.card import CardService
from statement.services.core.transaction import TransactionService


def get_invoice_by_year_and_month(card_id, year, month, user):
    """
    Obtém a fatura associada a um cartão para um ano e mês específicos.

    Parameters:
    - card_id: O ID do cartão para o qual a fatura será recuperada.
    - year: O ano para o qual a fatura será recuperada.
    - month: O mês para o qual a fatura será recuperada.
    - user: O usuário associado ao cartão.

    Returns:
    A fatura correspondente ao cartão, ano e mês fornecidos.

    Raises:
    Http404: Se nenhuma fatura for encontrada para o cartão, ano e mês fornecidos.
    """
    kwargs = {
        'payment_date__year': year,
        'payment_date__month': month,
        'user': user,
        'card': CardService.get_by_id(card_id),
        'home_screen': True,
    }
    invoice = TransactionService.get_by_filter(**kwargs)
    if invoice:
        return invoice
    raise Http404
