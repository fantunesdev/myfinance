from statement.models import Notification
from statement.services.base_service import BaseService


class NotificationService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Notification."""

    model = Notification

    @classmethod
    def get_by_filter(cls, order=None, first=False, **kwargs):
        """
        Obtém os lançamentos de acordo com filtros passados em um dicionário. Podendo ordenar por
        algum campo selecionado.
        """
        if first:
            return Notification.objects.filter(**kwargs).first()
        transactions = Notification.objects.filter(**kwargs)
        if order:
            return transactions.order_by(order)
        return transactions

    @staticmethod
    def build_transaction_from_notification(notification, user, card=None):
        from django.utils import timezone
        from statement.utils.transaction_input import parse_notification

        transaction = parse_notification(notification)
        created_at = getattr(notification, 'created_at', None)
        if created_at is None:
            notification_date = timezone.localdate()
        else:
            notification_date = timezone.localtime(created_at).date() if timezone.is_aware(created_at) else created_at.date()
        transaction.update({
            'card': card,
            'type': 'saida',
            'posted_date': notification_date,
            'payment_date': notification_date,
        })
        return transaction
