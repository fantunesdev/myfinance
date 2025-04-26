from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from oauth2_provider.models import Application

User = get_user_model()


class Command(BaseCommand):
    """
    'Cria um app OAuth2 para o Transaction Classifier'
    """

    help = 'Cria um app OAuth2 para o Transaction Classifier'

    def handle(self, *args, **options):
        username = 'transaction-classifier'
        application_name = 'Transaction Classifier'

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Usuário {username} não encontrado'))
            self.show_create_user_tutorial()
            return

        if Application.objects.filter(user=user, name=application_name).exists():
            self.stdout.write(self.style.WARNING(f'Aplicação {application_name} já existente.'))
            self.show_create_user_tutorial()
            return

        app = Application.objects.create(
            name=application_name,
            user=user,
            client_type=Application.CLIENT_CONFIDENTIAL,
        )

        self.stdout.write(self.style.SUCCESS(f'Aplicação {application_name} criada com sucesso!'))
        self.stdout.write(f'Client ID: {app.client_id}')
        self.stdout.write(f'Client Secret: {app.client_secret}')

    def show_create_user_tutorial(self):
        """
        Exibe o tutorial para criação de usuário.
        """
        self.stdout.write('Para criar o usuário:')
        self.stdout.write('')
        self.stdout.write('> python manage.py shell')
        self.stdout.write('')
        self.stdout.write('from django.contrib.auth import get_user_model')
        self.stdout.write('')
        self.stdout.write('User = get_user_model()')
        self.stdout.write('')
        self.stdout.write('User.objects.create_user(')
        self.stdout.write('    username="transaction-classifier",')
        self.stdout.write('    email="email@exemplo.com",')
        self.stdout.write('    name="Transaction Classifier",')
        self.stdout.write('    password="senha_forte",')
        self.stdout.write('    is_active=True,')
        self.stdout.write('    is_staff=True,')
        self.stdout.write(')')
