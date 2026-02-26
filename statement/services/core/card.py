import re

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

        Valida através do:
        - app_id do cartão (card.account.app_id)
        - 4 últimos dígitos do cartão na mensagem da notificação

        :param card: O cartão a ser verificado.
        :param notification: A notificação a ser verificada.
        :return: True se a notificação pertence ao cartão, False caso contrário.
        """
        # Require app_id match first (notification.app identifies the bank)
        # print(f"Notification.app={notification.app}, Card's bank app_id={card.account.bank.app_id}")
        if notification.app != card.account.bank.app_id:
            return False

        # If notification has a user, ensure it matches card.user (new requirement)
        if getattr(notification, 'user', None) is not None:
            if notification.user_id != getattr(card.user, 'id', None):
                return False

        # Prefer matching by card number when card has numbers registered.
        card_numbers = list(card.card_numbers.all())
        if card_numbers:
            # Try to extract the last 4 digits from the notification message (e.g. "final 8599")
            match = re.search(r'final\s+(\d{4})', (notification.message or ''), re.IGNORECASE)
            if match:
                last_four_digits = match.group(1)
                for card_number in card_numbers:
                    number_without_spaces = (card_number.number or '').replace(' ', '')
                    if number_without_spaces.endswith(last_four_digits):
                        return True
                # If message contains final but none of the card numbers match, do NOT bind
                return False

        # Fallback/default: bind by user + app_id (already checked app_id above).
        # If notification.user is None and card has no numbers, we avoid binding to be safe.
        if getattr(notification, 'user', None) is not None:
            return notification.user_id == getattr(card.user, 'id', None)

        return False

    @staticmethod
    def are_notifications_owner(cards, notifications):
        """
        Verifica a quais cartões pertencem as notificações.

        Adiciona um atributo 'card_id' em cada notificação com o ID do cartão proprietário.

        :param cards: Uma lista de cartões a serem verificados.
        :param notifications: uma lista de notificações a serem verificadas.
        :return: Dicionário mapeando cada notificação aos cartões que a possuem,
                 e adicionando atributo 'card_id' na notificação.
        """
        result = {}

        for notification in notifications:
            result[notification.id] = []
            # Inicializa card_id como None
            notification.card_id = None
            # Inicializa card_number como None
            notification.card_number = None
            notification.card_number_id = None

            for card in cards:
                try:
                    is_owner = CardService.is_notification_owner(card, notification)
                except Exception:
                    is_owner = False


                if is_owner:
                    result[notification.id].append(card)
                    # Adiciona o ID do cartão à notificação (usa o primeiro match)
                    if notification.card_id is None:
                        notification.card_id = card.id
                        notification.card = card
                    # Se o cartão possui números, tenta identificar o CardNumber correspondente
                    try:
                        card_numbers = list(card.card_numbers.all())
                        if card_numbers:
                            match = re.search(r'final\s+(\d{4})', (notification.message or ''), re.IGNORECASE)
                            if match:
                                last_four_digits = match.group(1)
                                for card_number in card_numbers:
                                    number_without_spaces = (card_number.number or '').replace(' ', '')
                                    if number_without_spaces.endswith(last_four_digits):
                                        notification.card_number = card_number
                                        notification.card_number_id = card_number.id
                                        break
                    except Exception:
                        # Não faz nada por que alguns cartões não tem card numbers.
                        pass

        return result
