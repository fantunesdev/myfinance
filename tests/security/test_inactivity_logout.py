import pytest
from django.conf import settings
from django.test import Client, override_settings

from login.forms.user_forms import InactivityLogoutForm
from login.models import Profile, User


@pytest.fixture
def web_settings():
    with override_settings(
        ROOT_URLCONF='myfinance.urls',
        INSTALLED_APPS=[*settings.INSTALLED_APPS, *[
            app for app in ('django.contrib.admin', 'oauth2_provider') if app not in settings.INSTALLED_APPS
        ]],
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'login.middleware.PrivatePageCacheMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ],
        TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True,
                    'OPTIONS': {'context_processors': [
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                        'login.context_processors.inactivity_logout',
                    ]}}],
        ALLOWED_HOSTS=['testserver'], LOGIN_URL='/login/',
    ):
        yield


@pytest.fixture
def browser_client(db, web_settings):
    user = User.objects.create_user(username='idle-user', name='Idle user', email='idle@example.invalid', password='Secret!123')
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    return client, user


@pytest.mark.parametrize('minutes', ['', '0', '-1', '1441', '1.5', 'invalid'])
def test_enabled_setting_requires_valid_integer_minutes(minutes):
    form = InactivityLogoutForm({'inactivity_logout_enabled': 'on', 'inactivity_logout_minutes': minutes})
    assert not form.is_valid()
    assert 'inactivity_logout_minutes' in form.errors


def test_disabled_setting_accepts_empty_minutes():
    form = InactivityLogoutForm({'inactivity_logout_minutes': ''})
    assert form.is_valid(), form.errors
    assert form.cleaned_data['inactivity_logout_minutes'] == 10


def test_setting_updates_only_current_user_and_publishes_config(browser_client):
    client, user = browser_client
    other = User.objects.create(username='other-idle', name='Other user', email='other-idle@example.invalid')
    other_profile = Profile.objects.create(user=other)
    response = client.get('/usuarios/perfil/inatividade/editar/')
    assert response.status_code == 200
    assert b'inactivity-logout-config' in response.content
    assert 'no-store' in response.headers['Cache-Control']
    csrf = client.cookies['csrftoken'].value
    response = client.post('/usuarios/perfil/inatividade/editar/', {
        'inactivity_logout_enabled': 'on', 'inactivity_logout_minutes': '5',
    }, HTTP_X_CSRFTOKEN=csrf)
    assert response.status_code == 302
    profile = Profile.objects.get(user=user)
    assert profile.inactivity_logout_enabled
    assert profile.inactivity_logout_minutes == 5
    other_profile.refresh_from_db()
    assert not other_profile.inactivity_logout_enabled
    response = client.get('/usuarios/perfil/')
    assert response.status_code == 200
    assert 'Privacidade e segurança' in response.content.decode()
    assert '"enabled": true' in response.content.decode()


def test_logout_requires_post_csrf_and_matching_browser_session(browser_client):
    client, _ = browser_client
    client.get('/usuarios/perfil/inatividade/editar/')
    token = client.session['inactivity_browser_id']
    csrf = client.cookies['csrftoken'].value
    url = '/usuarios/inatividade/logout/'
    assert client.get(url).status_code == 405
    assert client.post(url, {'session': token}).status_code == 403
    assert client.post(url, {'session': 'old-session'}, HTTP_X_CSRFTOKEN=csrf).status_code == 409
    assert client.post(url, {'session': 'sessão-antiga'}, HTTP_X_CSRFTOKEN=csrf).status_code == 409
    assert '_auth_user_id' in client.session
    assert client.post(url, {'session': token}, HTTP_X_CSRFTOKEN=csrf).status_code == 200
    assert '_auth_user_id' not in client.session
    assert client.get('/usuarios/perfil/').status_code == 302
    assert 'Você saiu por inatividade' in client.get('/login/?inactive=1').content.decode()


def test_logout_leaves_other_browser_sessions_authenticated(browser_client):
    client, user = browser_client
    other = Client()
    other.force_login(user)
    client.get('/usuarios/perfil/inatividade/editar/')
    response = client.post('/usuarios/inatividade/logout/', {
        'session': client.session['inactivity_browser_id'],
    }, HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
    assert response.status_code == 200
    assert '_auth_user_id' in other.session
    assert other.get('/usuarios/perfil/inatividade/editar/').status_code == 200
