import secrets
import time

from django.urls import reverse

from login.models import Profile


def inactivity_logout(request):
    if not request.user.is_authenticated:
        return {}
    # Isolate browser sessions; an old page must never log out a newer login.
    if 'inactivity_browser_id' not in request.session:
        request.session['inactivity_browser_id'] = secrets.token_urlsafe(24)
    profile = Profile.objects.filter(user=request.user).first()
    return {'inactivity_logout_config': {
        'session': request.session['inactivity_browser_id'],
        'enabled': bool(profile and profile.inactivity_logout_enabled),
        'minutes': profile.inactivity_logout_minutes if profile else 10,
        'revision': str(time.time_ns()),
        'logoutUrl': reverse('inactivity_logout'),
        'loginUrl': reverse('login_user') + '?inactive=1',
    }}
