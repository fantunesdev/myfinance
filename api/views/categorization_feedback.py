import os
import requests
from datetime import datetime
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response

from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from statement.models import CategorizationFeedback
from statement.services.core.categorization_feedback import CategorizationFeedbackService
from statement.views.core.categorization_feedback import CategorizationFeedbackView as StatementView
from statement.utils.jwt import JWTUtils


class CategorizationFeedbackView(BaseView):
    """
    Classe que gerencia a view das cartões na API.
    """

    model = CategorizationFeedback
    service = CategorizationFeedbackService
    serializer = BaseSerializer
    statement_view = StatementView

    @action(detail=False, methods=['get'], url_path='retrain')
    def retrain_from_feedback(self, request):
        """
        Retreina o modelo do usuário no Transaction Classifier a partir dos feedbacks dados pelo usuários.


        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        """
        try:
            # Obtém os feedbacks não treinados
            feedbacks = self.service.get_untrained()

            if not feedbacks.exists():
                return Response(
                    {"message": "Nenhum feedback disponível para treinamento."},
                    status=status.HTTP_204_NO_CONTENT
                )

            # Envia os feedbacks para o microserviço
            microservice_response = self._train_from_feedback(feedbacks, request.user)

            # Marca os feedbacks como treinados
            for feedback in feedbacks:
                self.service.set_as_trained(feedback)

            return Response(
                {
                    "message": "Feedbacks enviados e marcados como treinados com sucesso.",
                    "microservice_response": microservice_response,
                },
                status=status.HTTP_200_OK
            )
        except requests.exceptions.RequestException as e:
            # Trata erros de comunicação com o microserviço
            return Response(
                {"error": f"Erro ao comunicar com o microserviço: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            # Trata erros gerais
            return Response(
                {"error": f"Ocorreu um erro inesperado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _train_from_feedback(self, feedbacks, user):
        """
        Envia os feedbacks para o microserviço de treinamento.

        TODO: separar esses métodos de conexão com o microserviço numa classe em statement/integrations/transaction_classifier.py

        :param feedbacks: QuerySet de feedbacks.
        :param user: Usuário autenticado.
        """
        uri = os.getenv('TRANSACTION_CLASSIFIER_URL')
        port = os.getenv('TRANSACTION_CLASSIFIER_PORT')
        endpoint = 'feedback'
        token = JWTUtils.generate_access_token_for_user(user)

        url = f'{uri}:{port}/{endpoint}'

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
        }

        serializer = self.serializer(feedbacks, many=True, model=CategorizationFeedback)
        response = requests.post(url, headers=headers, json=serializer.data, timeout=10)
        response.raise_for_status()
        return response.json()
