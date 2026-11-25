from oauth2_provider.oauth2_validators import OAuth2Validator


class TwoFactorOAuthValidator(OAuth2Validator):
    def validate_user(self, username, password, client, request, *args, **kwargs):
        if not super().validate_user(username, password, client, request, *args, **kwargs):
            return False
        return not request.user.two_factor_enabled

    def save_bearer_token(self, token, request, *args, **kwargs):
        from django.db import transaction
        from login.models import User
        from oauthlib.oauth2 import InvalidGrantError
        from oauth2_provider.models import RefreshToken, Grant

        user = getattr(request, 'user', None)
        if user is None or request.grant_type == 'client_credentials':
            return super().save_bearer_token(token, request, *args, **kwargs)
        # Serialize issuance with MFA/email changes that revoke user grants.
        with transaction.atomic():
            current = User.objects.select_for_update().filter(pk=user.pk, is_active=True).first()
            if not current or (request.grant_type == 'password' and current.two_factor_enabled):
                raise InvalidGrantError()
            if (
                request.grant_type == 'refresh_token'
                and not RefreshToken.objects.filter(
                    user=current,
                    token=getattr(request, 'refresh_token', ''),
                ).exists()
            ):
                raise InvalidGrantError()
            if (
                request.grant_type == 'authorization_code'
                and not Grant.objects.filter(
                    user=current,
                    code=getattr(request, 'code', ''),
                ).exists()
            ):
                raise InvalidGrantError()
            request.user = current
            return super().save_bearer_token(token, request, *args, **kwargs)
