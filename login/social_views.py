"""Restricted entry points around the maintained OAuth implementation."""
import secrets
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from requests.exceptions import RequestException
from social_core.exceptions import SocialAuthBaseException
from social_django import views as social_views
from social_django.models import UserSocialAuth

from login.models import Profile, User
from login.pipeline import SocialLoginError


def is_enabled():
    return bool(
        getattr(settings, 'SOCIAL_LOGIN_ENABLED', False)
        and getattr(settings, 'SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', '')
        and getattr(settings, 'SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', '')
    )


def check_backend(backend):
    if backend != 'google-oauth2' or not is_enabled():
        raise Http404


@never_cache
@require_POST
def begin(request, backend):
    check_backend(backend)
    if request.user.is_authenticated and Profile.objects.filter(user=request.user, social_login_enabled=False).exists():
        messages.error(request, 'Ative o login social no perfil antes de conectar ou confirmar sua conta Google.')
        return redirect('get_profile')
    # Bind this flow to the local identity that explicitly initiated it.
    request.session['google_flow_user'] = str(request.user.pk) if request.user.is_authenticated else ''
    request.session['google_flow_at'] = time.time()
    # Only fixed local destinations; discard caller-supplied next entirely.
    request.session.pop('next', None)
    request.POST = request.POST.copy()
    request.POST.pop('next', None)
    request.GET = request.GET.copy()
    request.GET.pop('next', None)
    return social_views.auth(request, backend)


@never_cache
@require_GET
def complete(request, backend):
    check_backend(backend)
    expected_user = request.session.pop('google_flow_user', None)
    started = request.session.pop('google_flow_at', 0)
    current_user = str(request.user.pk) if request.user.is_authenticated else ''
    destination = 'get_profile' if request.user.is_authenticated else 'login_user'
    if expected_user is None or expected_user != current_user or not 0 <= time.time() - started <= 600:
        messages.error(request, 'A sessão de autenticação expirou. Inicie o acesso com Google novamente.')
        return redirect(destination)
    request.session.pop('next', None)
    request.GET = request.GET.copy()
    request.GET.pop('next', None)
    try:
        result = social_views.complete(request, backend)
    except (SocialAuthBaseException, RequestException) as error:
        message = (
            str(error)
            if isinstance(error, SocialLoginError)
            else 'Não foi possível autenticar com Google. Tente novamente.'
        )
        messages.error(request, message)
        return redirect(destination)
    if request.user.is_authenticated:
        request.session['inactivity_browser_id'] = secrets.token_urlsafe(24)
        request.session['google_reauthenticated'] = {'user': str(request.user.pk), 'at': time.time()}
    return result


@never_cache
@login_required
@require_POST
def disconnect(request, backend, association_id):
    check_backend(backend)
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.pk)
        association = UserSocialAuth.objects.filter(pk=association_id, provider=backend, user=user).first()
        if association is None:
            raise Http404
        if (
            not user.has_usable_password()
            and not UserSocialAuth.objects.filter(user=user).exclude(pk=association.pk).exists()
        ):
            messages.error(request, 'Defina uma senha antes de desconectar seu único método de acesso.')
        else:
            association.delete()
            request.session.pop('google_reauthenticated', None)
            messages.success(request, 'Conta Google desconectada.')
    return redirect('get_profile')


@never_cache
@login_required
@require_POST
def update_preference(request):
    value = request.POST.get('enabled')
    if value not in ('true', 'false'):
        return HttpResponseBadRequest('Informe se deseja ativar ou desativar o login social.')
    enabled = value == 'true'
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.pk)
        profile, _ = Profile.objects.get_or_create(user=user)
        if not enabled and not user.has_usable_password():
            messages.error(request, 'Defina uma senha antes de desativar o login social para manter acesso à conta.')
        else:
            profile.social_login_enabled = enabled
            profile.save(update_fields=['social_login_enabled'])
            request.session.pop('google_reauthenticated', None)
            messages.success(
                request,
                'Login social ativado para sua conta.' if enabled else 'Login social desativado para sua conta.',
            )
    return redirect('get_profile')
