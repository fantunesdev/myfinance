from statement.models import Notification
from statement.services.base_service import BaseService

class NotificationService(BaseService):
    """ Serviço para gerenciar operações relacionadas ao modelo Notification. """

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
