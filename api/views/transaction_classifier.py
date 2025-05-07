from requests.exceptions import RequestException
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from clients.transaction_classifier.transaction_classifier import TransactionClassifierClient
from statement.services.core.categorization_feedback import CategorizationFeedbackService


class TransactionClassifierView(ViewSet):
    """
    Classe que gerencia as views de conexão com o TransactionClassifierClient
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='status')
    def status(self, request):
        """
        Obtém o status de treinamento do modelo do usuário.

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        """
        try:
            microservice_client = TransactionClassifierClient(request.user)
            response = microservice_client.status()
            return Response({'message': response['message']}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='subcategory/train')
    def subcategory_train(self, request):
        """
        Treina o modelo do usuário no Transaction Classifier.

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        """
        try:
            CategorizationFeedbackService.reset_subcategory_feedback(request.user)
            microservice_client = TransactionClassifierClient(request.user)
            response = microservice_client.subcategory.train()
            return Response({'message': response['message']}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='subcategory/feedback')
    def subcategory_feedback(self, request):
        """
        Retreina o modelo do usuário no Transaction Classifier a partir dos feedbacks dados pelo usuários.

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        """
        try:
            # Obtém os feedbacks não treinados
            feedbacks = CategorizationFeedbackService.get_subcategory_untrained(request.user)

            if not feedbacks.exists():
                return Response(
                    {'error': 'Nenhum feedback disponível para treinamento.'}, status=status.HTTP_404_NOT_FOUND
                )

            # Envia os feedbacks para o micro serviço
            microservice_client = TransactionClassifierClient(request.user)
            microservice_response = microservice_client.subcategory.retrain_from_feedback(feedbacks)

            # Marca os feedbacks como treinados
            for feedback in feedbacks:
                CategorizationFeedbackService.set_subcategory_training_status(feedback)

            return Response(
                {
                    'message': 'Feedbacks enviados e marcados como treinados com sucesso.',
                    'microservice_response': microservice_response,
                },
                status=status.HTTP_200_OK,
            )
        except RequestException as e:
            # Trata erros de comunicação com o micro serviço
            return Response(
                {'error': f'Erro ao comunicar com o micro serviço: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            # Trata erros gerais
            return Response(
                {'error': f'Ocorreu um erro inesperado: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='subcategory/delete')
    def delete_subcategory_feedbacks(self, request):
        """
        Apaga os feedbacks usados para treinamento

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        """

        feedbacks = CategorizationFeedbackService.get_subcategory_untrained(request.user)

        if not feedbacks:
            return

        for feedback in feedbacks:
            feedback.delete()

    @action(detail=False, methods=['post'], url_path='description/train')
    def description_train(self, request):
        """
        Treina o modelo do usuário no Transaction Classifier.

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        """
        try:
            CategorizationFeedbackService.reset_description_feedback(request.user)
            microservice_client = TransactionClassifierClient(request.user)
            response = microservice_client.description.train()
            return Response({'message': response['message']}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='description/feedback')
    def description_feedback(self, request):
        """
        Retreina o modelo do usuário no Transaction Classifier a partir dos feedbacks dados pelo usuários.

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        """
        try:
            # Obtém os feedbacks não treinados
            feedbacks = CategorizationFeedbackService.get_description_untrained(request.user)

            if not feedbacks.exists():
                return Response(
                    {'error': 'Nenhum feedback disponível para treinamento.'}, status=status.HTTP_404_NOT_FOUND
                )

            # Envia os feedbacks para o micro serviço
            microservice_client = TransactionClassifierClient(request.user)
            microservice_response = microservice_client.description.retrain_from_feedback(feedbacks)

            # Marca os feedbacks como treinados
            for feedback in feedbacks:
                CategorizationFeedbackService.set_description_training_status(feedback)

            return Response(
                {
                    'message': 'Feedbacks enviados e marcados como treinados com sucesso.',
                    'microservice_response': microservice_response,
                },
                status=status.HTTP_200_OK,
            )
        except RequestException as e:
            # Trata erros de comunicação com o micro serviço
            return Response(
                {'error': f'Erro ao comunicar com o micro serviço: {str(e)}'}, status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            # Trata erros gerais
            return Response(
                {'error': f'Ocorreu um erro inesperado: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='delete')
    def delete_feedbacks(self, request):
        """
        Apaga os feedbacks usados para treinamento

        :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
        """
        CategorizationFeedbackService.delete_feedbacks(request.user)
