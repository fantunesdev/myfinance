"""
Gera um token a partir
"""
import uuid
import dataclasses
from datetime import timedelta

from django.conf import settings
from jose import jwt

from statement.utils.datetime import DateTimeUtils


@dataclasses.dataclass
class JWTUtils:
    """
    Classe que gerencia a autenticação via JWT.
    """

    @staticmethod
    def generate_token(user):
        """
        Cria um token de autenticação para o usuário conectado.
        """
        payload = {
            'user_id': user.id,
            'username': user.username,
            'token_type': 'access',
            'exp': DateTimeUtils.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': DateTimeUtils.now(),
            'jti': str(uuid.uuid4()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
