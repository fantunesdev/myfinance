from datetime import timedelta

import pytest
from django.conf import settings
from django.test import override_settings
from django.utils import timezone
from test_identity_two_factor import (
    BASE,
    account,
    authenticated,
    enable,
    otp,
    web,  # noqa: F401 -- shared autouse pytest fixture
)

from login import security
from login.account_email import process_account_email
from login.models import AccountEmailDelivery, SecurityAuditEvent, TwoFactorDevice


@pytest.mark.django_db
@pytest.mark.parametrize('state', ['inactive', 'missing', 'disabled', 'unconfirmed', 'expired_enrollment', 'locked'])
def test_factor_verification_rejects_ineligible_device_states(state):
    user = account()
    secret = enable(user)
    device = TwoFactorDevice.objects.get(user=user)
    if state == 'inactive':
        user.is_active = False
        user.save()
    elif state == 'missing':
        device.delete()
    elif state == 'disabled':
        user.two_factor_enabled = False
        user.save()
    elif state == 'unconfirmed':
        device.confirmed = False
        device.save()
    elif state == 'expired_enrollment':
        device.pending_created_at = timezone.now() - timedelta(minutes=11)
        device.save()
    else:
        device.locked_until = timezone.now() + timedelta(minutes=5)
        device.save()
    assert not security.verify_factor(user, otp(secret), enrollment=state == 'expired_enrollment')


@pytest.mark.django_db
def test_factor_verification_fails_closed_when_rate_limit_cache_is_unavailable(mocker):
    mocker.patch('login.security.cache.add', side_effect=RuntimeError('cache unavailable'))
    assert not security.attempt_allowed(account(), '127.0.0.1')


@pytest.mark.parametrize('scope', [{}, {'user': None}, {'session': {}}])
def test_websocket_security_rejects_incomplete_scopes(scope):
    assert not security.verified_websocket_session(scope)


@pytest.mark.django_db
@pytest.mark.parametrize('layer_mode', ['none', 'working', 'offline'])
def test_security_changes_notify_after_commit_and_tolerate_outages(
    mocker, django_capture_on_commit_callbacks, layer_mode
):
    user = account()
    layer = None if layer_mode == 'none' else mocker.Mock(group_send=mocker.AsyncMock())
    if layer_mode == 'offline':
        layer.group_send.side_effect = RuntimeError('offline')
    mocker.patch('channels.layers.get_channel_layer', return_value=layer)
    with django_capture_on_commit_callbacks(execute=True):
        security.security_changed(user, event='test-security-change')
    assert SecurityAuditEvent.objects.filter(user=user, kind='test-security-change').exists()
    if layer:
        layer.group_send.assert_awaited_once_with(f'user_updates_{user.pk}', {'type': 'security_changed'})


@pytest.mark.django_db
def test_security_changes_revoke_all_human_oauth_grants(mocker):
    user = account()
    with override_settings(INSTALLED_APPS=[*settings.INSTALLED_APPS, 'oauth2_provider']):
        filters = [
            mocker.patch(f'oauth2_provider.models.{name}.objects.filter')
            for name in ('AccessToken', 'RefreshToken', 'Grant')
        ]
        security.security_changed(user)
        for query in filters:
            query.assert_called_once_with(user=user)
            query.return_value.delete.assert_called_once()


@pytest.mark.django_db
def test_account_confirmation_delivery_retries_then_discards_undeliverable_mail(mocker):
    user = account()
    authenticated(user).post(BASE + 'email/', {'email': 'pending@example.com'})
    mocker.patch('login.account_email.EmailMessage.send', return_value=0)
    for attempt in range(3):
        AccountEmailDelivery.objects.update(available_at=timezone.now() - timedelta(seconds=1))
        assert process_account_email()
        if attempt < 2:
            queued = AccountEmailDelivery.objects.get()
            assert queued.claim is None and queued.locked_until is None
            assert queued.available_at > timezone.now()
    assert not AccountEmailDelivery.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize('state', ['inactive', 'attempts_exhausted', 'stale_credentials', 'unknown_kind'])
def test_stale_or_ineligible_confirmation_deliveries_are_discarded(state):
    user = account()
    authenticated(user).post(BASE + 'email/', {'email': 'pending@example.com'})
    if state == 'inactive':
        user.is_active = False
        user.save()
    elif state == 'attempts_exhausted':
        AccountEmailDelivery.objects.update(attempts=3)
    elif state == 'stale_credentials':
        user.set_password('DifferentPassword!123')
        user.save()
    else:
        AccountEmailDelivery.objects.update(kind='unknown')
    assert process_account_email()
    assert not AccountEmailDelivery.objects.exists()


@pytest.mark.django_db
def test_email_change_throttling_returns_form_error_without_queueing_mail(mocker):
    user = account()
    mocker.patch('login.account_email.allow_request', return_value=False)
    response = authenticated(user).post(BASE + 'email/', {'email': 'pending@example.com'})
    assert response.status_code == 200
    assert response.context['form'].non_field_errors()
    assert not AccountEmailDelivery.objects.exists()


@pytest.mark.django_db
def test_factor_management_rejects_unknown_actions():
    assert authenticated(account()).post(BASE + '2fa/gerenciar/', {'action': 'invalid'}).status_code == 400
