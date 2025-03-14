"""
Este módulo fornece serviços relacionados extratos das contas do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.http import Http404

from statement.services.core.account import AccountService
from statement.services.core.transaction import TransactionService


def get_extract_by_year_and_month(account_id, year, month, user):
    """
    Obtém o extrato financeiro associado a uma conta para um ano e mês específicos.

    Parameters:
    - account_id: O ID da conta para a qual o extrato será recuperado.
    - year: O ano para o qual o extrato será recuperado.
    - month: O mês para o qual o extrato será recuperado.
    - user: O usuário associado à conta.

    Returns:
    O extrato financeiro correspondente à conta, ano e mês fornecidos.

    Raises:
    Http404: Se nenhum extrato for encontrado para a conta, ano e mês fornecidos.
    """
    kwargs = {
        'payment_date__year': year,
        'payment_date__month': month,
        'user': user,
        'account': AccountService.get_by_id(account_id),
        'home_screen': True,
    }
    extract = TransactionService.get_by_filter(**kwargs)
    if extract:
        return extract
    raise Http404
