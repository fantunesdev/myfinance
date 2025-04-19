from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Gerenciador para objetos User."""
    def create_user(self, username, email, name, password=None, **extra_fields):
        """
        Cria e salva um User com o nome de usuário, email e senha fornecidos.

        :param username: O nome de usuário do novo usuário.
        :param email: O endereço de email do novo usuário.
        :param name: O nome completo do novo usuário.
        :param password: A senha para o novo usuário.
        :param extra_fields: Campos adicionais a serem definidos no modelo User.
        :raises ValueError: Se o nome de usuário ou email não forem fornecidos.
        :returns: O objeto User recém-criado.
        """
        if not username:
            raise ValueError("O nome de usuário é obrigatório")
        if not email:
            raise ValueError("O email é obrigatório")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, name, password=None, **extra_fields):
        """
        Cria e salva um Superusuário com o nome de usuário, email e senha fornecidos.

        :param username: O nome de usuário do novo superusuário.
        :param email: O endereço de email do novo superusuário.
        :param name: O nome completo do novo superusuário.
        :param password: A senha para o novo superusuário.
        :param extra_fields: Campos adicionais a serem definidos no modelo User.
        :returns: O objeto User do superusuário recém-criado.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superusuário precisa ter is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superusuário precisa ter is_superuser=True.")

        return self.create_user(username, email, name, password, **extra_fields)
