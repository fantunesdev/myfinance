import pytest
from asgiref.sync import async_to_sync

from api.websockets.consumers.update_consumer import UpdateConsumer
from login.models import User


@pytest.mark.parametrize(
    'handler', ['send_websocket_update', 'investments_changed', 'classifier_changed', 'security_changed']
)
def test_websocket_handlers_close_unverified_sessions_without_sending_data(mocker, handler):
    consumer = UpdateConsumer()
    consumer.scope = {'user': User(two_factor_enabled=True)}
    consumer.close = mocker.AsyncMock()
    consumer.send_json = mocker.AsyncMock()
    async_to_sync(getattr(consumer, handler))({'type': handler, 'revision': 'r', 'job': {}})
    consumer.close.assert_awaited_once_with(code=4401)
    consumer.send_json.assert_not_called()


def test_websocket_connect_rejects_an_authenticated_user_without_mfa(mocker):
    consumer = UpdateConsumer()
    consumer.scope = {'user': User(two_factor_enabled=True)}
    consumer.close = mocker.AsyncMock()
    async_to_sync(consumer.connect)()
    consumer.close.assert_awaited_once_with(code=4401)


@pytest.mark.django_db
def test_websocket_session_policy_rechecks_the_current_database_identity():
    user = User.objects.create(username='ws-policy', email='ws-policy@test.invalid')
    consumer = UpdateConsumer()
    consumer.scope = {
        'user': user,
        'session': {'_auth_user_id': str(user.pk), '_auth_user_hash': user.get_session_auth_hash()},
    }
    assert async_to_sync(consumer.security_allowed)()
    User.objects.filter(pk=user.pk).update(security_version=1)
    assert not async_to_sync(consumer.security_allowed)()


def test_websocket_disconnect_is_safe_before_group_registration():
    async_to_sync(UpdateConsumer().disconnect)(1000)
