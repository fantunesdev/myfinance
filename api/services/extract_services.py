"""
Este módulo fornece serviços relacionados extratos das contas do usuário, seguindo o padrão de repositório
para interagir com o banco de dados e fornecer suas respectivas funcionalidades.
"""

from django.http import Http404

from statement.services import extract_services


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
    extract = extract_services.get_extract_by_account_year_and_month(account_id, year, month, user)
    if extract:
        return extract
    raise Http404
