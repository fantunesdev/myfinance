import pytest
from django.urls import reverse

from login.models import Profile, User
from statement.models import AppConfig, Notification, NotificationTitle


def test_registration_creates_a_profile_and_hashes_the_password(authenticated_web):
    response = authenticated_web.client.post(
        reverse('create_user'),
        {
            'username': 'new-account',
            'name': 'New account',
            'email': 'new-account@test.invalid',
            'password1': 'SafePassword!123',
            'password2': 'SafePassword!123',
        },
    )
    assert response.status_code == 302
    user = User.objects.get(username='new-account')
    assert user.check_password('SafePassword!123')
    assert Profile.objects.filter(user=user).exists()


def test_invalid_registration_preserves_form_errors(authenticated_web):
    response = authenticated_web.client.post(
        reverse('create_user'),
        {
            'username': 'new-account',
            'name': 'New',
            'email': 'new@test.invalid',
            'password1': 'SafePassword!123',
            'password2': 'Different!123',
        },
    )
    assert response.status_code == 200
    assert 'password2' in response.context['user_form'].errors
    assert not User.objects.filter(username='new-account').exists()


@pytest.mark.parametrize('route', ['update_profile', 'update_configs'])
@pytest.mark.parametrize('valid', [True, False])
def test_profile_editing_updates_only_valid_submissions(authenticated_web, route, valid):
    response = authenticated_web.client.post(
        reverse(route), {'username': 'renamed' if valid else '', 'name': 'Updated'}
    )
    assert response.status_code == (302 if valid else 200)
    authenticated_web.user.refresh_from_db()
    assert authenticated_web.user.name == ('Updated' if valid else 'Coverage')


def test_password_change_preserves_the_current_authenticated_session(authenticated_web):
    response = authenticated_web.client.post(
        reverse('change_password'),
        {
            'old_password': 'Coverage!123',
            'new_password1': 'UpdatedPassword!123',
            'new_password2': 'UpdatedPassword!123',
        },
    )
    assert response.status_code == 302
    authenticated_web.user.refresh_from_db()
    assert authenticated_web.user.check_password('UpdatedPassword!123')
    assert authenticated_web.client.get(reverse('get_profile')).status_code == 200


def test_mfa_password_change_requires_recent_authentication(authenticated_web):
    authenticated_web.user.two_factor_enabled = True
    authenticated_web.user.save()
    response = authenticated_web.client.get(reverse('change_password'))
    assert response.status_code == 302
    assert reverse('security_reauthenticate') in response.url


@pytest.mark.parametrize('route', ['edit_user_notification_titles', 'edit_notification_titles'])
def test_notification_preferences_can_be_cleared_and_service_failures_are_nonfatal(authenticated_web, mocker, route):
    title = NotificationTitle.objects.create(title='Compra')
    client = authenticated_web.client
    assert client.post(reverse(route), {'enabled_ids': [title.pk]}).status_code == 302
    assert authenticated_web.user.notification_title_preferences.get(title=title).enabled
    assert client.post(reverse(route), {}).status_code == 302
    assert not authenticated_web.user.notification_title_preferences.get(title=title).enabled
    mocker.patch(
        'statement.services.core.notification_title.NotificationTitleService.set_user_enabled_titles',
        side_effect=RuntimeError('offline'),
    )
    assert client.post(reverse(route), {}).status_code == 302
    assert client.get(reverse(route)).status_code == 302


@pytest.mark.parametrize('target', ['NotificationTitleService.ensure_titles', 'NotificationService.get_by_filter'])
def test_notification_preferences_page_handles_unavailable_data(authenticated_web, mocker, target):
    mocker.patch('login.views.' + target, side_effect=RuntimeError('unavailable'))
    response = authenticated_web.client.get(reverse('user_notification_titles'))
    assert response.status_code == 200
    assert response.context['notification_titles'] == []


@pytest.mark.parametrize('failure', ['config', 'notifications', 'titles', 'classifier'])
def test_profile_page_handles_optional_service_failures(authenticated_web, mocker, failure):
    AppConfig.objects.create(enable_transaction_classifier=failure == 'classifier')
    Notification.objects.create(user=authenticated_web.user, app='app', title='Compra', message='message')
    target = {
        'config': 'AppConfig.get_solo',
        'notifications': 'NotificationService.get_by_filter',
        'titles': 'NotificationTitleService.ensure_titles',
        'classifier': 'TransactionClassifierClient',
    }[failure]
    mocker.patch('login.views.' + target, side_effect=RuntimeError('unavailable'))
    response = authenticated_web.client.get(reverse('get_profile'))
    assert response.status_code == 200
    if failure == 'classifier':
        assert response.context['transaction_classifier_enabled']
        assert len(response.context['transaction_classifier']) == 2


def test_profile_shows_available_classifier_status(authenticated_web, mocker):
    AppConfig.objects.create(enable_transaction_classifier=True)
    mocker.patch('login.views.TransactionClassifierClient').return_value.status.return_value = {'data': []}
    assert authenticated_web.client.get(reverse('get_profile')).context['transaction_classifier'] == []


def test_logout_clears_the_authenticated_session(authenticated_web):
    response = authenticated_web.client.get(reverse('logout_user'))
    assert response.status_code == 302
    assert '_auth_user_id' not in authenticated_web.client.session


@pytest.mark.parametrize('valid', [True, False])
def test_password_login_accepts_only_valid_credentials(authenticated_web, valid):
    client = authenticated_web.client
    client.logout()
    response = client.post(
        reverse('login_user'),
        {
            'username': authenticated_web.user.username,
            'password': 'Coverage!123' if valid else 'incorrect',
        },
    )
    assert response.status_code == (302 if valid else 200)
    assert ('_auth_user_id' in client.session) is valid


def test_login_rejects_credentials_revoked_between_form_validation_and_authentication(authenticated_web, mocker):
    client = authenticated_web.client
    client.logout()
    mocker.patch('login.views.authenticate', return_value=None)
    response = client.post(
        reverse('login_user'), {'username': authenticated_web.user.username, 'password': 'Coverage!123'}
    )
    assert response.status_code == 200
    assert '_auth_user_id' not in client.session
