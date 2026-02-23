import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification, NotificationTitle

logger = logging.getLogger('myfinance')


@receiver(post_save, sender=Notification)
def ensure_notification_title_exists(sender, instance, created, **kwargs):
    """
    Garante que exista um registro em NotificationTitle para o título da Notification.
    Executado sempre que uma Notification é salva; usa get_or_create para evitar
    duplicatas e falha silenciosa caso a tabela não exista (migrações pendentes).
    """
    try:
        if not instance or not getattr(instance, 'title', None):
            return

        NotificationTitle.objects.get_or_create(title=instance.title)
    except Exception as e:
        # Não interromper fluxo de criação de notificações por conta deste processo.
        logger.warning('Não foi possível criar NotificationTitle para "%s": %s', getattr(instance, 'title', None), str(e))
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from statement.models import CardNumber, Card, Transaction


@receiver(post_save, sender=CardNumber)
def update_transactions_on_cardnumber_save(sender, instance, **kwargs):
    """When a CardNumber is saved, update related transactions to inherit its home_screen."""
    Transaction.objects.filter(card_number=instance).update(home_screen=instance.home_screen)


@receiver(post_delete, sender=CardNumber)
def update_transactions_on_cardnumber_delete(sender, instance, **kwargs):
    """When a CardNumber is deleted, transactions linked to it should fallback to card.home_screen."""
    fallback = instance.card.home_screen if getattr(instance, 'card', None) else False
    Transaction.objects.filter(card_number_id=getattr(instance, 'id', None)).update(home_screen=fallback, card_number=None)


@receiver(post_save, sender=Card)
def update_transactions_on_card_save(sender, instance, **kwargs):
    """When a Card's home_screen is changed, update transactions that don't have a CardNumber."""
    # First, propagate the card's home_screen to its CardNumber children so their
    # own post_save signal will update related transactions. We save each
    # CardNumber to ensure `post_save` handlers run (QuerySet.update would
    # bypass signals).
    try:
        for cn in instance.card_numbers.all():
            if cn.home_screen != instance.home_screen:
                cn.home_screen = instance.home_screen
                cn.save(update_fields=['home_screen'])
    except Exception:
        # If something unexpected happens, still update transactions without card_number.
        pass

    # Update transactions that reference the card but don't have a specific card_number.
    Transaction.objects.filter(card=instance, card_number__isnull=True).update(home_screen=instance.home_screen)
