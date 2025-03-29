"""
Autentificação
"""

import json
import uuid
from datetime import timedelta

from django.contrib.auth import authenticate
from django.http import JsonResponse
from jose import jwt
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from statement.utils.datetime import DateTimeUtils

class AuthenticationView:
    """
    Classe que gerencia a autenticação via JWT.
    """

    @csrf_exempt
    def get_token(self, request):
        """
        Faz o login de um usuário retornando um token
        """
        if request.method != 'POST':
            return JsonResponse({'error': 'Método não permitido'}, status=405)

        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')

        user = authenticate(request, username=username, password=password)
        if not user:
            return JsonResponse({'error': 'Credenciais inválidas'}, status=401)

        token = self.generate_jwt_token(user)
        return JsonResponse({'token': token})

    @staticmethod
    def generate_jwt_token(user):
        """
        Cria um token de autenticação para o usuário conectado.
        """
        payload = {
            'user_id': user.id,  # Mantenha apenas um campo para o ID do usuário
            'username': user.username,
            'token_type': 'access',
            'exp': DateTimeUtils.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': DateTimeUtils.now(),
            'jti': str(uuid.uuid4()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
