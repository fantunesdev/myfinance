import re
from datetime import datetime

from clients.transaction_classifier.transaction_classifier import TransactionClassifierClient
from statement.models import AppConfig, Notification
from statement.services.base_service import BaseService
from statement.services.core.category import CategoryService


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
    def build_transaction_from_notification(notification, card=None):
        """
        Monta a estrutura básica de um lançamento a partir de uma notificação.

        Extrai informações da notificação:
        - date: Data da notificação
        - value: Valor em reais (padrão: R$ XX,XX)
        - description: Estabelecimento (entre "em" e caracteres de pontuação)
        - card: Cartão associado (opcional)

        :param notification: A notificação a ser processada
        :param card: O cartão associado à transação (opcional)
        :return: Dicionário com os dados da transação
        """
        transaction = {
            'card': card,
            'type': 'saida',  # Notificações geralmente são despesas
            'original_description': notification.message if hasattr(notification, 'message') else '',
        }

        # Extrai a data da notificação
        try:
            notification_date = datetime.strptime(notification.created_at.strftime('%Y-%m-%d'), '%Y-%m-%d').date()
            transaction['release_date'] = notification_date
            transaction['payment_date'] = notification_date
        except (ValueError, AttributeError):
            # Se falhar, tenta usar o campo "date" se existir na mensagem
            transaction['release_date'] = datetime.now().date()
            transaction['payment_date'] = datetime.now().date()

        # Extrai o valor (padrão: R$ XX,XX ou R$ XX.XXX,XX)
        value_match = re.search(r'R\$\s*([\d.,]+)', notification.message)
        if value_match:
            value_str = value_match.group(1)
            # Converte formato brasileiro (XX,XX) para float
            value_str = value_str.replace('.', '').replace(',', '.')
            try:
                transaction['value'] = float(value_str)
            except ValueError:
                transaction['value'] = 0.0
        else:
            transaction['value'] = 0.0

        # Extrai a descrição do estabelecimento (entre "em" e ponto/vírgula)
        # Padrão: "...em ESTABELECIMENTO. A compra..."
        desc_match = re.search(r'em\s+([A-Za-záéíóúàâêôãõç\s]+?)[\.,]', notification.message, re.IGNORECASE)
        if desc_match:
            transaction['description'] = desc_match.group(1).strip().upper()
        else:
            # Se não encontrar, usa parte do title
            transaction['description'] = notification.title

        # If global config enables classifier, try to predict category/subcategory/description
        try:
            if AppConfig.get_solo().enable_transaction_classifier:
                microservice_client = TransactionClassifierClient(None)
                # Use message/title for prediction
                text_for_prediction = notification.message or notification.title
                predicted = microservice_client.predict(text_for_prediction, '')
                if predicted:
                    transaction['category'] = predicted.get('category_id')
                    transaction['subcategory'] = predicted.get('subcategory_id')
                    transaction['description'] = predicted.get('description') or transaction.get('description')
                    # If category was predicted, try to set the transaction type accordingly
                    if transaction.get('category'):
                        try:
                            cat = CategoryService.get_by_id(transaction['category'])
                            transaction['type'] = cat.type
                        except Exception:
                            pass
        except Exception:
            # Do not fail notification processing if classifier is down
            pass

        return transaction
