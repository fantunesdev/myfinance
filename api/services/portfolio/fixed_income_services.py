from django.http import Http404

from statement.services.portfolio.fixed_income.fixed_income import FixedIncomeService


class FixedIncomeServices:
    """
    Service responsável por recuperar os dados registrados no banco
    """

    @classmethod
    def get_investment_progression(cls, user):
        """
        Obtém todos os bancos associadas a um usuário.

        Parameters:
        - user: O usuário para o qual os bancos devem ser recuperadas.

        Returns:
        Uma lista de bancos associadas ao usuário fornecido.

        Raises:
        Http404: Se nenhum banco estiver associado ao usuário.
        """
        fixed_income_progression = FixedIncomeService.get_investment_progression(user)
        if fixed_income_progression:
            return fixed_income_progression
        return Http404
