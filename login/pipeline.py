"""Application-owned user provisioning; provider tokens are not persisted."""
import secrets

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from social_core.exceptions import AuthException
from social_django.models import UserSocialAuth

from login.models import Profile, User


class SocialLoginError(AuthException):
    pass


def provision_user(backend, uid, details, response, user=None, social=None, id_key='sub', **kwargs):
    verified = response.get('email_verified') is True or response.get('verified_email') is True
    email = details.get('email', '').strip()
    try:
        validate_email(email)
    except ValidationError:
        raise SocialLoginError(backend, 'O Google precisa informar um e-mail válido e verificado.')
    if not verified or not uid:
        raise SocialLoginError(backend, 'O Google precisa informar um e-mail verificado.')
    if user and not user.is_active:
        raise SocialLoginError(backend, 'Esta conta está desativada.')

    try:
        with transaction.atomic():
            if user is None:
                if User.objects.filter(email__iexact=email).exists():
                    raise SocialLoginError(
                        backend,
                        'Este e-mail já está cadastrado. Entre pelo método atual e conecte o Google no perfil.',
                    )
                # Random usernames also avoid collisions with user-chosen local names.
                username = 'google_' + secrets.token_hex(16)
                while User.objects.filter(username=username).exists():
                    username = 'google_' + secrets.token_hex(16)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    name=(details.get('fullname') or email.split('@')[0])[:150],
                )
            else:
                user = User.objects.select_for_update().get(pk=user.pk)
                if not user.is_active:
                    raise SocialLoginError(backend, 'Esta conta está desativada.')
            profile, _ = Profile.objects.get_or_create(user=user)
            if not profile.social_login_enabled:
                raise SocialLoginError(
                    backend, 'O login social está desativado para esta conta. Entre com usuário e senha.'
                )
            if social is None:
                social = UserSocialAuth.objects.create(user=user, provider=backend.name, uid=str(uid), id_key=id_key)
    except IntegrityError:
        # Roll back user/profile as well if two callbacks race for one identity.
        raise SocialLoginError(backend, 'Não foi possível conectar a conta. Tente novamente ou use o acesso atual.')
    return {'user': user, 'social': social}
