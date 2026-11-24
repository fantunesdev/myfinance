import secrets
import time

from django.urls import reverse

from login.models import Profile
from statement.models import Version


def app_version(request):
    if not request.user.is_authenticated:
        return {}
    return {'app_version': Version.objects.order_by('-id').values_list('version', flat=True).first()}


def inactivity_logout(request):
    if not request.user.is_authenticated:
        return {}
    # Isolate browser sessions; an old page must never log out a newer login.
    if 'inactivity_browser_id' not in request.session:
        request.session['inactivity_browser_id'] = secrets.token_urlsafe(24)
    profile = Profile.objects.filter(user=request.user).first()
    return {
        'inactivity_logout_config': {
            'session': request.session['inactivity_browser_id'],
            'enabled': bool(profile and profile.inactivity_logout_enabled),
            'minutes': profile.inactivity_logout_minutes if profile else 10,
            'revision': str(time.time_ns()),
            'logoutUrl': reverse('inactivity_logout'),
            'loginUrl': reverse('login_user') + '?inactive=1',
        }
    }


def social_login(request):
    from social_django.models import UserSocialAuth

    from login.social_views import is_enabled

    enabled = is_enabled()
    accounts = (
        UserSocialAuth.objects.filter(user=request.user, provider='google-oauth2')
        if enabled and request.user.is_authenticated
        else []
    )
    profile = Profile.objects.filter(user=request.user).first() if request.user.is_authenticated else None
    return {
        'google_login_enabled': enabled,
        'google_accounts': accounts,
        'user_social_login_enabled': profile.social_login_enabled if profile else True,
    }
