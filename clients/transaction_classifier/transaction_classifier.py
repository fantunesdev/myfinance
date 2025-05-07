import json
import os
from typing import Union

import requests

from api.serializers.base_serializer import BaseSerializer
from clients.transaction_classifier.description_predictor import DescriptionPredictorClient
from clients.transaction_classifier.subcategory_predictor import SubcategoryPredictorClient
from clients.transaction_classifier.base_microservice import BaseMicroserviceClient
from statement.models import CategorizationFeedback
from statement.utils.jwt import JWTUtils
from statement.utils.utils import DictToObject
from statement.utils.datetime import DateTimeUtils


class TransactionClassifierClient(BaseMicroserviceClient):
    """
    Cliente para consumir o micro serviço Transaction Classifier
    """

    def __init__(self, user):
        super().__init__(user)
        self.subcategory = SubcategoryPredictorClient(user)
        self.description = DescriptionPredictorClient(user)


    def status(self):
        """
        Envia uma solicitação para o micro serviço para obter o status de treinamento do modelo do usuário.
        """
        response = self._send_requisition('status', 'get')
        self._handle_status_data(response)
        return response

    def predict(self, description: str, category: str = ''):
        """
        Faz uma previsão
        """
        predicted = {}
        predicted |= self.subcategory.predict(description, category)
        predicted |= self.description.predict(description)
        return predicted

    def _handle_status_data(self, response):
        """
        Transforma o dicionário da resposta do status em um objeto e realiza a conversão da data.

        :param response: dict - A resposta do micro serviço contendo as informações de status.
        :return: None - O método modifica a resposta diretamente, substituindo o valor da chave 'data'.
        """
        for i, _ in enumerate(response['data']):
            date = response['data'][i]['date']
            if date:
                response['data'][i]['date'] = DateTimeUtils.string_to_date(date)
            response['data'][i] = DictToObject(response['data'][i])
