from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import bank_serializer
from api.services import account_services, bank_services


class BankList(APIView):
    def get(self, request):
        accounts = account_services.get_accounts(request.user)
        banks = []
        for account in accounts:
            banks.append(bank_services.get_bank_by_id(account.bank.id))
        serializer = bank_serializer.BankSerializer(banks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BankDetails(APIView):
    def get(self, request, bank_id):
        bank = bank_services.get_bank_by_id(bank_id)
        serializer = bank_serializer.BankSerializer(bank)
        return Response(serializer.data, status=status.HTTP_200_OK)
