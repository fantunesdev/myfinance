from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from login.authentication import SecureJWTAuthentication, SecureSessionAuthentication, valid_token_policy
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenObtainSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.settings import api_settings
from login.models import User
from login.security import verify_factor


class SecureTokenSerializer(TokenObtainPairSerializer):
    otp = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=64)

    def validate(self, attrs):
        TokenObtainSerializer.validate(self, attrs)
        user = self.user
        if user.two_factor_enabled:
            request = self.context.get('request')
            ip = request.META.get('REMOTE_ADDR', '') if request else ''
            if not verify_factor(user, attrs.get('otp', ''), ip=ip):
                raise AuthenticationFailed('Código do autenticador ou de recuperação inválido, ausente ou bloqueado.')
        refresh = self.get_token(user)
        refresh['security_version'] = user.security_version
        refresh['amr'] = ['pwd', 'otp'] if user.two_factor_enabled else ['pwd']
        return {'refresh': str(refresh), 'access': str(refresh.access_token)}


class SecureRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        token = RefreshToken(attrs['refresh'])
        user = User.objects.filter(pk=token.get(api_settings.USER_ID_CLAIM), is_active=True).first()
        if not user or not valid_token_policy(user, token):
            raise AuthenticationFailed('Entre novamente para renovar o acesso.')
        return super().validate(attrs)


@method_decorator(sensitive_post_parameters(), name='dispatch')
class SecureTokenView(TokenObtainPairView):
    serializer_class = SecureTokenSerializer


class SecureRefreshView(TokenRefreshView):
    serializer_class = SecureRefreshSerializer
