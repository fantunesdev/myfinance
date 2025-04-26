"""
Gera um token a partir
"""
import dataclasses
import os
import uuid
from datetime import timedelta

from django.conf import settings
from jose import jwt
from rest_framework_simplejwt.tokens import RefreshToken

from statement.utils.datetime import DateTimeUtils

CLIENT_SECRET = os.getenv('CLIENT_SECRET')


@dataclasses.dataclass
class JWTUtils:
    """
    Classe que gerencia a autenticação via JWT.
    """

    @staticmethod
    def generate_token(user):
        """
        Cria um token de autenticação para o usuário conectado.

        :param user (:obj:`User`): O objeto do usuário autenticado proveniente de `requests.user`.
        :returns: str - O token de acesso JWT codificado.
        """
        payload = {
            'user_id': user.id,
            'username': user.username,
            'token_type': 'access',
            'exp': DateTimeUtils.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': DateTimeUtils.now(),
            'jti': str(uuid.uuid4()),
        }
        return jwt.encode(payload, CLIENT_SECRET, algorithm=settings.ALGORITHM)

    @staticmethod
    def generate_access_token_for_user(user):
        """
        Cria um token JWT a partir do usuário logado.

        :param user (:obj:`User`): O objeto do usuário autenticado proveniente de `requests.user`.
        :returns: str - O token de acesso JWT como uma string.
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
