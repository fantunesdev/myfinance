import json

from api.serializers.base_serializer import BaseSerializer
from clients.transaction_classifier.base_microservice import BaseMicroserviceClient
from statement.models import CategorizationFeedback


class SubcategoryPredictorClient(BaseMicroserviceClient):
    """Ciente do preditor de subcategorias do micro servico TransactionClassifier"""

    def train(self):
        """
        Envia uma solicitação para o micro serviço treinar o modelo com base nos dados do usuário.
        """
        return self._send_requisition('subcategories_predictor/train', 'post')

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
        return self._send_requisition('subcategories_predictor/predict', 'post', body)

    def predict_batch(self, transactions: list):
        """
        Envia uma lista de previsões para o micro serviço.

        :param transactions: Uma lista de lançamentos com dicionários.
        :example: {'description': 'Alguma descrição' , 'category': ''}
        """
        transactions_json = json.dumps(transactions)
        return self._send_requisition('subcategories_predictor/predict-batch', 'post', transactions_json)

    def retrain_from_feedback(self, feedbacks: list):
        """
        Envia o feedback do usuário para o modelo ser retreinado

        :param feedbacks: Uma lista de feedbacks dados pelo usuário
        """
        serializer = BaseSerializer(feedbacks, many=True, model=CategorizationFeedback)
        return self._send_requisition('subcategories_predictor/feedback', 'post', serializer.data)
