import os
from datetime import datetime

import requests
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from clients.transaction_classifier import TransactionClassifierClient
from statement.models import CategorizationFeedback
from statement.services.core.categorization_feedback import CategorizationFeedbackService
from statement.views.core.categorization_feedback import CategorizationFeedbackView as StatementView


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
                    {'message': 'Nenhum feedback disponível para treinamento.'}, status=status.HTTP_204_NO_CONTENT
                )

            # Envia os feedbacks para o microserviço
            microservice_client = TransactionClassifierClient(request.user)
            microservice_response = microservice_client.retrain_from_feedback(feedbacks)

            # Marca os feedbacks como treinados
            for feedback in feedbacks:
                self.service.set_as_trained(feedback)

            return Response(
                {
                    'message': 'Feedbacks enviados e marcados como treinados com sucesso.',
                    'microservice_response': microservice_response,
                },
                status=status.HTTP_200_OK,
            )
        except requests.exceptions.RequestException as e:
            # Trata erros de comunicação com o microserviço
            return Response(
                {'error': f'Erro ao comunicar com o microserviço: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            # Trata erros gerais
            return Response(
                {'error': f'Ocorreu um erro inesperado: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
