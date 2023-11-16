from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import transaction_serializer
from api.services import extract_services


class ExtractByAccountYearAndMonth(APIView):
    def get(self, request, account_id, year, month):
        extract = extract_services.get_extract_by_year_and_month(account_id, year, month, request.user)
        serializer = transaction_serializer.TransactionSerializer(extract, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
