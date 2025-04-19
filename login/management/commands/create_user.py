from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import getpass

User = get_user_model()

class Command(BaseCommand):
    """
    Cria um usuário interativamente.
    """
    help = 'Cria um usuário interativamente.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Criando novo usuário:'))

        username = input('Username: ')
        email = input('Email: ')
        name = input('Nome: ')
        password = getpass.getpass('Senha: ')
        password2 = getpass.getpass('Confirme a senha: ')

        if password != password2:
            self.stdout.write(self.style.ERROR('As senhas não coincidem.'))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'O usuário "{username}" já existe.'))
            return

        user = User.objects.create_user(
            username=username,
            email=email,
            name=name,
            password=password,
        )
        user.is_active = True
        user.is_staff = True
        user.save()

        self.stdout.write(self.style.SUCCESS(f'Usuário "{username}" criado com sucesso!'))
