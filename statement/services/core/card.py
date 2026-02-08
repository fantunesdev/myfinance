from statement.models import Card
from statement.services.base_service import BaseService
import re


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
        # Verifica se o app da notificação bate com o app_id do banco
        if notification.app != card.account.bank.app_id:
            return False
        
        # Extrai os 4 últimos dígitos da mensagem (padrão: "final 8599")
        match = re.search(r'final\s+(\d{4})', notification.message, re.IGNORECASE)
        if not match:
            return False
        
        last_four_digits = match.group(1)
        
        # Verifica se algum número de cartão vinculado termina com esses dígitos
        card_numbers = card.card_numbers.all()
        for card_number in card_numbers:
            # Remove espaços em branco e pega os últimos 4 dígitos
            number_without_spaces = card_number.number.replace(' ', '')
            if number_without_spaces.endswith(last_four_digits):
                return True
        
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
            
            for card in cards:
                if CardService.is_notification_owner(card, notification):
                    result[notification.id].append(card)
                    # Adiciona o ID do cartão à notificação (usa o primeiro match)
                    if notification.card_id is None:
                        notification.card_id = card.id
                        notification.card = card
        
        return result
