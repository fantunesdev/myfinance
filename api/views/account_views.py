from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import account_serializer
from api.services import account_services


class AccountsList(APIView):
    def get(self, request):
        accounts = account_services.get_accounts(request.user)
        serializer = account_serializer.AccountSerializer(accounts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
