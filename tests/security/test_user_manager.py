import pytest

from login.models import User


@pytest.mark.django_db
@pytest.mark.parametrize('field', ['username', 'email'])
def test_user_creation_requires_identity_fields(field):
    data = {'username': 'required-fields', 'email': 'required@test.invalid', 'name': 'Required'}
    data[field] = ''
    with pytest.raises(ValueError):
        User.objects.create_user(**data)
    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize('field', ['is_staff', 'is_superuser'])
def test_superuser_cannot_disable_required_privileges(field):
    with pytest.raises(ValueError):
        User.objects.create_superuser('admin-test', 'admin@test.invalid', 'Admin', **{field: False})
    assert not User.objects.exists()


@pytest.mark.django_db
def test_superuser_has_required_flags_normalized_email_and_hashed_password():
    user = User.objects.create_superuser('admin-test', 'admin@EXAMPLE.COM', 'Admin', 'SecureTest!123')
    assert user.is_active and user.is_staff and user.is_superuser
    assert user.email == 'admin@example.com'
    assert user.check_password('SecureTest!123')
    assert user.password != 'SecureTest!123'
