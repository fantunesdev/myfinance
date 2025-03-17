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
