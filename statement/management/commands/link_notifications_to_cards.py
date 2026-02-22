from django.core.management.base import BaseCommand
from statement.services.core.card import CardService
from statement.services.core.notification import NotificationService
from statement.models import Notification


class Command(BaseCommand):
    help = 'Vincula notificações existentes aos cartões com base no padrão "final XXXX"'

    def handle(self, *args, **options):
        # Busca todas as notificações sem cartão associado
        unlinked_notifications = Notification.objects.filter(card__isnull=True)
        
        if not unlinked_notifications.exists():
            self.stdout.write(self.style.SUCCESS('Nenhuma notificação sem cartão associado.'))
            return
        
        # Busca todos os cartões
        cards = list(CardService.model.objects.all())
        
        linked_count = 0
        failed_count = 0
        
        for notification in unlinked_notifications:
            # Tenta achar o cartão para essa notificação
            for card in cards:
                if CardService.is_notification_owner(card, notification):
                    notification.card = card
                    notification.save()
                    linked_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Notificação {notification.id} vinculada ao cartão {card.description}'
                        )
                    )
                    break
            else:
                failed_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'✗ Notificação {notification.id} não pôde ser vinculada (padrão não encontrado)'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{linked_count} notificações vinculadas. {failed_count} notificações sem vínculo.'
            )
        )
