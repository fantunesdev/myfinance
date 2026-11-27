from types import SimpleNamespace

import pytest
from rest_framework.exceptions import AuthenticationFailed

from login.models import User
from statement.authentication import DeviceTokenAuthentication
from statement.models import Device


@pytest.mark.parametrize('header', [None, b'Basic token', b'\xff token', b'Bearer unknown'])
@pytest.mark.django_db
def test_unrecognized_device_credentials_allow_other_authentication_backends(header):
    request = SimpleNamespace(headers={'authorization': header} if header else {})
    assert DeviceTokenAuthentication().authenticate(request) is None


@pytest.mark.parametrize('header', [b'Bearer', b'Bearer token extra', b'Bearer \xff'])
def test_malformed_device_credentials_are_rejected(header):
    with pytest.raises(AuthenticationFailed):
        DeviceTokenAuthentication().authenticate(SimpleNamespace(headers={'authorization': header}))


@pytest.mark.django_db
@pytest.mark.parametrize('active', [True, False])
def test_device_authentication_requires_an_active_owner(active):
    user = User.objects.create(username='device-auth', email='device-auth@test.invalid', is_active=active)
    device = Device.objects.create(user=user, name='Phone')
    request = SimpleNamespace(headers={'authorization': f'Bearer {device.token}'.encode()})
    if active:
        assert DeviceTokenAuthentication().authenticate(request) == (user, None)
    else:
        with pytest.raises(AuthenticationFailed, match='desativado'):
            DeviceTokenAuthentication().authenticate(request)
