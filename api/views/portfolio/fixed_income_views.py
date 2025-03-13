from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.services.portfolio.fixed_income_services import FixedIncomeServices


class FixedIncomeProgressionList(APIView):
    """
    Classe responsável pela construção das views dos investimentos de renda fixa
    """

    def get(self, request):
        """
        Obtém a progressão dos investimentos de renda ixa
        """
        fixed_income_progression = FixedIncomeServices.get_investment_progression(request.user)
        return Response(fixed_income_progression, status=status.HTTP_200_OK)
