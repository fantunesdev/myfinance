from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from login.models import User, TwoFactorDevice, RecoveryCode
from login.security import security_changed


class Command(BaseCommand):
    help = 'Recuperação administrativa de 2FA após verificar a identidade fora da aplicação. Invalida sessões e registra auditoria.'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('--reason', required=True)

    def handle(self, *args, **options):
        reason = options['reason'].strip()
        if len(reason) < 10 or len(reason) > 240:
            raise CommandError('Informe uma justificativa entre 10 e 240 caracteres, sem incluir segredos.')
        with transaction.atomic():
            user = User.objects.select_for_update().filter(username=options['username']).first()
            if not user:
                raise CommandError('Usuário não encontrado.')
            if not user.two_factor_enabled:
                raise CommandError('O usuário não tem 2FA ativo.')
            user.two_factor_enabled = False
            user.save(update_fields=['two_factor_enabled'])
            TwoFactorDevice.objects.filter(user=user).delete()
            RecoveryCode.objects.filter(user=user).delete()
            security_changed(user, event='administrative_2fa_recovery', reason=reason)
        self.stdout.write(
            self.style.SUCCESS(
                '2FA removido; sessões e acessos humanos anteriores invalidados. O usuário deve entrar novamente.'
            )
        )
