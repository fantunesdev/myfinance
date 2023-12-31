import json

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import transaction_serializer
from api.services import file_handler_services, transaction_services


class TransactionByYearAndMonth(APIView):
    def get(self, request, year, month):
        transactions = transaction_services.get_transactions_by_year_and_month(year, month, request.user)
        serializer = transaction_serializer.TransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TransactionYear(APIView):
    def get(self, request, year):
        transactions = transaction_services.get_transactions_by_year(year, request.user)
        serializer = transaction_serializer.TransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class ImportTransactions(APIView):
    def post(self, request):
        file_handler = file_handler_services.FileHandler(
            file=request.FILES.get('file'),
            account=request.data['account'],
            card=request.data['card'],
            user=request.user
        )     
        return Response(file_handler.transactions, status=status.HTTP_200_OK)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
