from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied


def valid_token_policy(user, token):
    return token.get('security_version', 0) == user.security_version and (
        not user.two_factor_enabled or token.get('amr') in (['pwd', 'otp'], ['service'])
    )


class SecureJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not valid_token_policy(user, validated_token):
            raise AuthenticationFailed('O acesso precisa ser renovado com o segundo fator.')
        return user


class SecureSessionAuthentication(SessionAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result and result[0].two_factor_enabled and request.session.get('mfa_version') != result[0].security_version:
            raise PermissionDenied('Confirme o segundo fator.')
        return result
