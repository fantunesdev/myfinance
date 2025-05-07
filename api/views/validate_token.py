from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from statement.utils.jwt import JWTUtils


class ValidateTokenView(APIView):
    """
    Classe que valida o token JWT.
    """

    def get(self, request):
        """
        Método GET para validar o token JWT.
        """
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return Response({'valid': False}, status=status.HTTP_401_UNAUTHORIZED)

        token = auth_header.split(' ')[1]

        if JWTUtils.verify_simplejwt_token(token):
            return Response({"valid": True}, status=status.HTTP_200_OK)
        return Response({'valid': False}, status=status.HTTP_401_UNAUTHORIZED)
