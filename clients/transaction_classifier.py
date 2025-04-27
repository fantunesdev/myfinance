import json
import os
from typing import Union

import requests

from api.serializers.base_serializer import BaseSerializer
from statement.models import CategorizationFeedback
from statement.utils.jwt import JWTUtils


class TransactionClassifierClient:
    """
    Cliente para consumir o micro serviço Transaction Classifier
    """

    BASE_URL = os.getenv('TRANSACTION_CLASSIFIER_URL')
    PORT = os.getenv('TRANSACTION_CLASSIFIER_PORT')

    def __init__(self, user):
        self._token = JWTUtils.generate_access_token_for_user(user)
        self._base_url = f'{self.BASE_URL}:{self.PORT}'
        self._headers = {'Authorization': f'Bearer {self._token}'}

    def _send_requisition(self, endpoint: str, body: Union[str, dict] = ''):
        """
        Método que envia requisições para o micro serviço.

        :param endpoint: O endpoint da requisição no micro serviço.
        :param body: Um json com o corpo da requisição serializado.
        """
        url = f'{self._base_url}/{endpoint}'
        response = requests.post(url, headers=self._headers, json=body, timeout=10)
        response.raise_for_status()
        return response.json()

    def train(self):
        """
        Envia uma solicitação para o micro serviço treinar o modelo com base nos dados do usuário.
        """
        return self._send_requisition('train')

    def predict(self, description: str, category: str = ''):
        """
        Envia uma solicitação de previsão para o micro serviço

        :param description: Uma descrição de lançamento.
        :param category: O nome de uma categoria.
        :returns
        """
        body = {
            'description': description,
            'category': category,
        }
        return self._send_requisition('predict', body)

    def predict_batch(self, transactions: list):
        """
        Envia uma lista de previsões para o micro serviço.

        :param transactions: Uma lista de lançamentos com dicionários.
        :example: {'description': 'Alguma descrição' , 'category': ''}
        """
        transactions_json = json.dumps(transactions)
        return self._send_requisition('predict-batch', transactions_json)

    def retrain_from_feedback(self, feedbacks: list):
        """
        Envia o feedback do usuário para o modelo ser retreinado

        :param feedbacks: Uma lista de feedbacks dados pelo usuário
        """
        serializer = BaseSerializer(feedbacks, many=True, model=CategorizationFeedback)
        return self._send_requisition('feedback', serializer.data)
