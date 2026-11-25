import time
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.test import Client, override_settings
from django.urls import include, path
from social_django.models import UserSocialAuth

from login import views
from login.models import Profile, User
from login.pipeline import SocialLoginError, provision_user

urlpatterns = [
    path('auth/', include('login.social_urls')),
    path('login/', views.login_user, name='login_user'),
    path('profile/', views.change_password, name='get_profile'),
    path('password/', views.change_password, name='change_password'),
]
PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'login.pipeline.provision_user',
)
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def web_settings():
    with override_settings(
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['testserver'],
        LOGIN_URL='/login/',
        SOCIAL_LOGIN_ENABLED=True,
        SOCIAL_AUTH_GOOGLE_OAUTH2_KEY='test-key',
        SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET='test-secret',
        SOCIAL_AUTH_GOOGLE_OAUTH2_USE_UNIQUE_USER_ID=True,
        SOCIAL_AUTH_GOOGLE_OAUTH2_ID_KEY='sub',
        SOCIAL_AUTH_PIPELINE=PIPELINE,
        SOCIAL_AUTH_LOGIN_REDIRECT_URL='/',
        SOCIAL_AUTH_NEW_ASSOCIATION_REDIRECT_URL='/profile/',
        AUTHENTICATION_BACKENDS=[
            'django.contrib.auth.backends.ModelBackend',
            'social_core.backends.google.GoogleOAuth2',
        ],
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ],
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': False,
                'OPTIONS': {
                    'loaders': [
                        ('django.template.loaders.locmem.Loader', {'index.html': '{% block content %}{% endblock %}'}),
                        'django.template.loaders.app_directories.Loader',
                    ],
                    'context_processors': [
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                        'login.context_processors.social_login',
                    ],
                },
            }
        ],
    ):
        yield


def local_user(**kwargs):
    return User.objects.create_user(
        username=kwargs.pop('username', 'local'), name='Local', email=kwargs.pop('email', 'local@example.com'), **kwargs
    )


def start(client):
    response = client.post('/auth/login/google-oauth2/', {'next': 'https://evil.invalid/'})
    assert response.status_code == 302
    return parse_qs(urlsplit(response.url).query)['state'][0]


def finish(client, state, sub='google-123', email='new@example.com', verified=True):
    with patch(
        'social_core.backends.google.GoogleOAuth2.request_access_token', return_value={'access_token': 'secret-token'}
    ), patch(
        'social_core.backends.google.GoogleOAuth2.user_data',
        return_value={'sub': sub, 'email': email, 'email_verified': verified, 'name': 'Google Name'},
    ):
        return client.get(
            '/auth/complete/google-oauth2/', {'state': state, 'code': 'test-code', 'next': 'https://evil.invalid/'}
        )


def test_new_and_returning_login_keep_stable_identity_and_local_data():
    client = Client()
    response = finish(client, start(client))
    assert response.status_code == 302 and response.url == '/'
    user = User.objects.get()
    assert user.name == 'Google Name' and not user.has_usable_password()
    assert not user.is_staff and not user.is_superuser
    assert Profile.objects.filter(user=user).count() == 1
    association = UserSocialAuth.objects.get()
    assert association.uid == 'google-123' and association.id_key == 'sub' and association.extra_data == {'email': 'new@example.com', 'email_verified': True}
    old_browser = client.session['inactivity_browser_id']
    client.logout()
    user.name = 'Edited locally'
    user.save()
    finish(client, start(client), email='changed@example.com')
    user.refresh_from_db()
    assert User.objects.count() == 1 and user.name == 'Edited locally' and user.email == 'new@example.com'
    assert client.session['inactivity_browser_id'] != old_browser


@pytest.mark.parametrize('verified,email', [(False, 'new@example.com'), (True, ''), (True, 'broken')])
def test_rejects_unverified_or_missing_email(verified, email):
    client = Client()
    assert finish(client, start(client), verified=verified, email=email).url == '/login/'
    assert not User.objects.exists()


def test_email_collision_requires_explicit_link_and_does_not_change_local_fields():
    user = local_user(email='New@example.com', password='LocalSecret!123')
    client = Client()
    assert finish(client, start(client)).url == '/login/'
    assert User.objects.count() == 1 and not UserSocialAuth.objects.exists()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    assert finish(client, start(client)).url == '/profile/'
    assert UserSocialAuth.objects.get().user == user
    user.refresh_from_db()
    assert user.name == 'Local' and user.check_password('LocalSecret!123')


def test_invalid_state_cancellation_and_expired_flow_do_not_login():
    client = Client()
    start(client)
    assert finish(client, 'wrong-state').url == '/login/'
    state = start(client)
    assert client.get('/auth/complete/google-oauth2/', {'error': 'access_denied', 'state': state}).url == '/login/'
    state = start(client)
    session = client.session
    session['google_flow_at'] = time.time() - 601
    session.save()
    assert finish(client, state).url == '/login/'
    assert not User.objects.exists()


def test_account_switch_during_flow_is_rejected():
    client = Client()
    state = start(client)
    client.force_login(local_user(), backend='django.contrib.auth.backends.ModelBackend')
    assert finish(client, state).url == '/profile/'
    assert not UserSocialAuth.objects.exists()


def test_inactive_user_and_already_owned_identity_are_rejected():
    owner = local_user(is_active=False)
    UserSocialAuth.objects.create(user=owner, provider='google-oauth2', uid='google-123')
    client = Client()
    assert finish(client, start(client)).url == '/login/'
    other = local_user(username='other', email='other@example.com')
    client.force_login(other, backend='django.contrib.auth.backends.ModelBackend')
    assert finish(client, start(client)).url == '/profile/'
    assert UserSocialAuth.objects.get().user == owner


def test_disconnect_requires_another_method_and_ownership():
    user = local_user()
    other = local_user(username='other', email='other@example.com')
    association = UserSocialAuth.objects.create(user=user, provider='google-oauth2', uid='123')
    client = Client()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    url = f'/auth/disconnect/google-oauth2/{association.pk}/'
    assert client.get(url).status_code == 405
    client.post(url)
    assert UserSocialAuth.objects.filter(pk=association.pk).exists()
    user.set_password('Secret!123')
    user.save()
    client.force_login(other, backend='django.contrib.auth.backends.ModelBackend')
    assert client.post(url).status_code == 404
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    assert client.post(url).status_code == 302
    assert not UserSocialAuth.objects.filter(pk=association.pk).exists()


def test_csrf_required_for_begin_and_disconnect():
    client = Client(enforce_csrf_checks=True)
    assert client.get('/auth/login/google-oauth2/').status_code == 405
    assert client.post('/auth/login/google-oauth2/').status_code == 403
    user = local_user()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    assert client.post('/auth/disconnect/google-oauth2/1/').status_code == 403


def test_disabled_feature_hides_button_and_blocks_routes():
    client = Client()
    with override_settings(SOCIAL_LOGIN_ENABLED=False):
        assert b'Entrar com Google' not in client.get('/login/').content
        assert client.post('/auth/login/google-oauth2/').status_code == 404
        assert client.get('/auth/complete/google-oauth2/').status_code == 404
    assert b'Entrar com Google' in client.get('/login/').content


def test_social_password_requires_recent_confirmation_and_preserves_session():
    client = Client()
    finish(client, start(client))
    user = User.objects.get()
    session = client.session
    session['google_reauthenticated'] = {'user': str(user.pk), 'at': time.time() - 301}
    session.save()
    assert (
        client.post('/password/', {'new_password1': 'NewSecret!123', 'new_password2': 'NewSecret!123'}).url
        == '/profile/'
    )
    assert not User.objects.get().has_usable_password()
    finish(client, start(client))
    assert (
        client.post('/password/', {'new_password1': 'NewSecret!123', 'new_password2': 'NewSecret!123'}).url
        == '/profile/'
    )
    assert User.objects.get().check_password('NewSecret!123')
    assert '_auth_user_id' in client.session
    assert 'google_reauthenticated' not in client.session


def test_atomic_creation_rolls_back_when_association_fails():
    from django.db import IntegrityError

    with patch.object(UserSocialAuth.objects, 'create', side_effect=IntegrityError):
        with pytest.raises(SocialLoginError):
            provision_user(
                SimpleNamespace(name='google-oauth2'), 'uid', {'email': 'new@example.com'}, {'email_verified': True}
            )
    assert not User.objects.exists() and not Profile.objects.exists()


def test_username_collision_is_resolved_without_reusing_local_account():
    local_user(username='google_collision')
    with patch('login.pipeline.secrets.token_hex', side_effect=['collision', 'unique']):
        result = provision_user(
            SimpleNamespace(name='google-oauth2'),
            'new-id',
            {'email': 'different@example.com'},
            {'email_verified': True},
        )
    assert result['user'].username == 'google_unique'
    assert Profile.objects.filter(user=result['user']).exists()


def test_local_password_change_still_requires_old_password():
    user = local_user(password='OldSecret!123')
    client = Client()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    response = client.post(
        '/password/', {'old_password': 'incorrect', 'new_password1': 'NewSecret!123', 'new_password2': 'NewSecret!123'}
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password('OldSecret!123')
    response = client.post(
        '/password/',
        {'old_password': 'OldSecret!123', 'new_password1': 'NewSecret!123', 'new_password2': 'NewSecret!123'},
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password('NewSecret!123') and '_auth_user_id' in client.session


def test_begin_accepts_valid_csrf_token_and_rejects_unknown_provider():
    client = Client(enforce_csrf_checks=True)
    client.get('/login/')
    token = client.cookies['csrftoken'].value
    response = client.post('/auth/login/google-oauth2/', HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 302
    assert urlsplit(response.url).netloc == 'accounts.google.com'
    assert client.post('/auth/login/unknown/', HTTP_X_CSRFTOKEN=token).status_code == 404
    with override_settings(SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=''):
        assert client.post('/auth/login/google-oauth2/', HTTP_X_CSRFTOKEN=token).status_code == 404


def test_user_can_disable_and_reenable_without_removing_google_link():
    client = Client()
    finish(client, start(client))
    user = User.objects.get()
    user.set_password('LocalSecret!123')
    user.save()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    association = UserSocialAuth.objects.get()
    other = local_user()
    other_profile = Profile.objects.create(user=other)
    response = client.post('/auth/preference/', {'enabled': 'false', 'user': other.pk})
    assert response.url == '/profile/'
    assert not Profile.objects.get(user=user).social_login_enabled
    other_profile.refresh_from_db()
    assert other_profile.social_login_enabled
    assert UserSocialAuth.objects.filter(pk=association.pk).exists()
    assert '_auth_user_id' in client.session
    assert client.post('/auth/login/google-oauth2/').url == '/profile/'
    client.logout()
    response = finish(client, start(client))
    assert response.url == '/login/' and '_auth_user_id' not in client.session
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    assert client.post('/auth/preference/', {'enabled': 'true'}).url == '/profile/'
    client.logout()
    finish(client, start(client))
    assert client.session['_auth_user_id'] == str(user.pk)
    assert UserSocialAuth.objects.count() == 1


def test_social_only_user_must_define_password_before_disabling():
    client = Client()
    finish(client, start(client))
    user = User.objects.get()
    assert client.post('/auth/preference/', {'enabled': 'false'}).url == '/profile/'
    assert Profile.objects.get(user=user).social_login_enabled
    assert UserSocialAuth.objects.filter(user=user).exists()


def test_disabled_preference_blocks_new_link_and_callback_started_before_disable():
    user = local_user(password='LocalSecret!123')
    profile = Profile.objects.create(user=user)
    client = Client()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    state = start(client)
    client.post('/auth/preference/', {'enabled': 'false'})
    assert finish(client, state).url == '/profile/'
    assert not UserSocialAuth.objects.exists()
    profile.refresh_from_db()
    assert not profile.social_login_enabled


def test_preference_requires_authenticated_post_and_csrf():
    client = Client(enforce_csrf_checks=True)
    assert client.post('/auth/preference/', {'enabled': 'false'}).status_code == 403
    user = local_user(password='LocalSecret!123')
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    assert client.get('/auth/preference/').status_code == 405
    assert client.post('/auth/preference/', {'enabled': 'false'}).status_code == 403
    client.get('/login/')
    csrf = client.cookies['csrftoken'].value
    assert client.post('/auth/preference/', {'enabled': 'false'}, HTTP_X_CSRFTOKEN=csrf).status_code == 302
    assert not Profile.objects.get(user=user).social_login_enabled
    anonymous = Client()
    assert anonymous.post('/auth/preference/', {'enabled': 'true'}).url.startswith('/login/')


@pytest.mark.parametrize('value', ['', 'invalid', '0'])
def test_invalid_preference_does_not_change_setting(value):
    user = local_user(password='LocalSecret!123')
    client = Client()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    assert client.post('/auth/preference/', {'enabled': value}).status_code == 400
    assert not Profile.objects.filter(user=user).exists()


def test_user_preference_can_be_managed_with_global_login_disabled():
    user = local_user(password='LocalSecret!123')
    client = Client()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    with override_settings(SOCIAL_LOGIN_ENABLED=False):
        assert client.post('/auth/preference/', {'enabled': 'false'}).status_code == 302
        assert not Profile.objects.get(user=user).social_login_enabled
        assert client.post('/auth/preference/', {'enabled': 'true'}).status_code == 302
        assert Profile.objects.get(user=user).social_login_enabled
        assert client.post('/auth/login/google-oauth2/').status_code == 404


def test_profile_shows_personal_preference_and_link_controls():
    from django.conf import settings

    user = local_user(password='LocalSecret!123')
    profile = Profile.objects.create(user=user)
    client = Client()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    with override_settings(
        ROOT_URLCONF='myfinance.urls',
        INSTALLED_APPS=[*settings.INSTALLED_APPS, 'django.contrib.admin', 'oauth2_provider'],
    ):
        response = client.get('/usuarios/perfil/')
        assert response.status_code == 200
        html = response.content.decode()
        assert 'Desativar login social' in html and 'Conectar ou confirmar conta Google' in html
        profile.social_login_enabled = False
        profile.save()
        html = client.get('/usuarios/perfil/').content.decode()
        assert 'Ativar login social' in html and 'Conectar ou confirmar conta Google' not in html
        with override_settings(SOCIAL_LOGIN_ENABLED=False):
            html = client.get('/usuarios/perfil/').content.decode()
            assert 'Ativar login social' in html and 'O administrador precisa configurar e habilitar a integração' in html
            assert 'Conexão com Google indisponível' in html
            assert 'Conectar conta Google</button>' not in html


def test_disabled_preference_blocks_login_and_signed_in_linking():
    user = local_user(password='LocalSecret!123')
    Profile.objects.create(user=user, social_login_enabled=False)
    association = UserSocialAuth.objects.create(user=user, provider='google-oauth2', uid='google-123', id_key='sub')
    client = Client()
    assert finish(client, start(client)).url == '/login/'
    assert '_auth_user_id' not in client.session
    assert UserSocialAuth.objects.filter(pk=association.pk).exists()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    assert client.post('/auth/login/google-oauth2/').url == '/profile/'
    client.post('/auth/preference/', {'enabled': 'true'})
    client.logout()
    assert finish(client, start(client)).url == '/'
    assert client.session['_auth_user_id'] == str(user.pk)


def test_disabling_during_google_flow_blocks_callback_and_preserves_other_user():
    user = local_user(password='LocalSecret!123')
    other = local_user(username='other', email='other@example.com')
    Profile.objects.create(user=other)
    client = Client()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    state = start(client)
    client.post('/auth/preference/', {'enabled': 'false', 'user_id': other.pk})
    assert finish(client, state).url == '/profile/'
    assert not UserSocialAuth.objects.exists()
    assert not Profile.objects.get(user=user).social_login_enabled
    assert Profile.objects.get(user=other).social_login_enabled
