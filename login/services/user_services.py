from datetime import date

from login.models import User


def create_user(user):
    return User.objects.create_user(
        username=user.username,
        password=user.password,
        name=user.name,
        email=user.email,
        is_superuser=user.is_superuser,
        is_staff=user.is_staff,
        is_active=user.is_active,
        date_joined=date.today(),
        photo=user.photo,
    )
