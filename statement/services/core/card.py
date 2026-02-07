from statement.models import Card
from statement.services.base_service import BaseService


class CardService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Card."""

    model = Card
    user_field = 'user'

    @staticmethod
    def set_processing_date(card, date):
        """
        Determina a data de vencimento a partir da data de fechamento do cartão
        """
        # TODO trocar o nome do campo de expiration_day para processing_day
        if card.closing_day < date.day:
            month = date.month + 1
            return date.replace(day=card.expiration_day, month=month)
        return date.replace(day=card.expiration_day)

    @staticmethod
    def is_notification_owner(card, notification):
        """
        Verifica se uma notificação pertence a um cartão específico
        
        :param card: O cartão a ser verificado.
        :param notification: A notificação a ser verificada.
        """

    @staticmethod
    def are_notifications_owner(cards, notifications):
        """
        Verifica a quais cartões pertencem as notificações.

        :param cards: Uma lista de cartões a serem verificados.
        :param notifications: uma lista de notificações a serem verificadas.
        """
