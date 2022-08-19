from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, name, email, username, password, is_superuser, is_staff, is_active, date_joined, photo):
        if not email:
            raise ValueError('O campo e-mail não foi informado.')
        if not username:
            raise ValueError('O campo username não foi informado.')
        user = self.model(
            username=username,
            name=name,
            email=self.normalize_email(email).lower(),
            is_superuser=is_superuser,
            is_staff=is_staff,
            is_active=is_active,
            date_joined=date_joined,
            photo=photo,
        )
        user.set_password(password)
        user.save()
        return user
