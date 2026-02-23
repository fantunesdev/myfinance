from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from statement.models import Device


class DeviceTokenAuthentication(BaseAuthentication):
    """Autenticação por token fixo de dispositivo.

    Lê o header `Authorization: Bearer <token>`. Se o token corresponder a um
    `Device.token`, autentica como `device.user`.

    Comportamento:
    - Se não houver header Authorization ou o esquema não for Bearer, retorna None
      para permitir que outras classes de autenticação (ex: JWT) sejam tentadas.
    - Se houver um Bearer token e corresponder a um `Device`, retorna (user, None).
    - Se houver um Bearer token que NÃO corresponda a um `Device`, retorna None
      para permitir que JWT trate o token. Caso nenhum sistema autentique, o DRF
      retornará 401 automaticamente.
    """

    keyword = 'Bearer'

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth:
            return None

        try:
            scheme = auth[0].decode()
        except Exception:
            return None

        if scheme.lower() != self.keyword.lower():
            return None

        if len(auth) == 1:
            raise AuthenticationFailed('Invalid token header. No credentials provided.')
        if len(auth) > 2:
            raise AuthenticationFailed('Invalid token header. Token string should not contain spaces.')

        try:
            token = auth[1].decode()
        except Exception:
            raise AuthenticationFailed('Invalid token header. Token not decodable.')

        try:
            device = Device.objects.get(token=token)
        except Device.DoesNotExist:
            # Não consideramos falha imediata aqui para não bloquear JWT.
            return None

        return (device.user, None)
