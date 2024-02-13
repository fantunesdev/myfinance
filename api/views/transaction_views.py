import json

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import file_handler_serializer, transaction_serializer
from api.services import file_handler_services, transaction_services
from statement.entities.transaction import Transaction
from statement.services import currency_services, transaction_services


class TransactionByYearAndMonth(APIView):
    """
    Esta classe trata os lançamentos da requisição quando recebem parâmetros
    relativos ano e ao mês.
    """

    def get(self, request, year, month):
        """
        Lista os lançamentos filtrando por ano e mês

        Parameters:
        - request (django.http.HttpRequest) - Uma instância que contém
        informações sobre a solicitação, como parâmetros de consulta,
        cabeçalhos, método HTTP, dados do corpo, etc.

        Returns:
        Em caso de sucesso, uma lista de objetos do tipo transactions. Em casso
        de falha, um código e uma mensagem de erro.
        """
        transactions = transaction_services.get_transactions_by_year_and_month(
            year, month, request.user
        )
        serializer = transaction_serializer.TransactionSerializer(
            transactions, many=True
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class TransactionYear(APIView):
    """
    Esta classe trata os lançamentos da requisição quando recebem um
    parâmetro relativo ao ano.
    """

    def get(self, request, year):
        """
        Lista os lançamentos filtrando por ano

        Parameters:
        - request (django.http.HttpRequest) - Uma instância que contém
        informações sobre a solicitação, como parâmetros de consulta,
        cabeçalhos, método HTTP, dados do corpo, etc.

        Returns:
        Em caso de sucesso, uma lista de objetos do tipo transactions. Em casso
        de falha, um código e uma mensagem de erro.
        """
        transactions = transaction_services.get_transactions_by_year(
            year, request.user
        )
        serializer = transaction_serializer.TransactionSerializer(
            transactions, many=True
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class TransactionsList(APIView):
    """
    Esta classe trata os lançamentos da requisição quando não recebem um
    parâmetro.
    """

    def post(self, request):
        """
        Cadastra o lançamento no banco de dados fazendo as validações.

        Parameters:
        - request (django.http.HttpRequest) - Uma instância que contém
        informações sobre a solicitação, como parâmetros de consulta,
        cabeçalhos, método HTTP, dados do corpo, etc.

        Returns:
        Em caso de sucesso, um objeto do tipo transactions, em casso de
        falha, um código e uma mensagem de erro.
        """
        request.data['user'] = request.user.id
        serializer = transaction_serializer.TransactionSerializer(
            data=request.data
        )
        if serializer.is_valid():
            new_transaction = Transaction(
                release_date=serializer.validated_data['release_date'],
                payment_date=serializer.validated_data['payment_date'],
                account=serializer.validated_data['account'],
                card=serializer.validated_data['card'],
                category=serializer.validated_data['category'],
                subcategory=serializer.validated_data['subcategory'],
                description=serializer.validated_data['description'],
                value=serializer.validated_data['value'],
                installments_number=0,
                paid=0,
                fixed=False,
                annual=False,
                currency=currency_services.get_currency_by_id('BRL'),
                observation=None,
                remember=False,
                type=serializer.validated_data['type'],
                effected=False,
                home_screen=serializer.validated_data['home_screen'],
                user=serializer.validated_data['user'],
                installment=None,
            )
            db_transaction = transaction_services.create_transaction(
                new_transaction
            )
            serializer = transaction_serializer.TransactionSerializer(
                db_transaction
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(
            {'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST
        )


class ImportTransactions(APIView):
    """
    Esta classe recebe e trata o arquivo de carga.
    """

    def post(self, request):
        """
        Recebe, valida o arquivo de carga, trata os lançamentos e devolve uma lista de lançamentos.

        Parameters:
        - request (django.http.HttpRequest) - Uma instância que contém
        informações sobre a solicitação, como parâmetros de consulta,
        cabeçalhos, método HTTP, dados do corpo, etc.

        Returns:
        list: Uma lista de objetos do tipo transactions.
        """
        serializer = file_handler_serializer.FileHandlerSerializer(request)
        if serializer.is_valid():
            try:
                file_handler = file_handler_services.FileHandler(request)
                return Response(
                    file_handler.transactions, status=status.HTTP_200_OK
                )
            except ObjectDoesNotExist:
                if request.data['account'] and not request.data['card']:
                    error_message = f'Não existe uma conta com o id {request.data["account"]}.'
                elif request.data['card'] and not request.data['account']:
                    error_message = f'Não existe um cartão com o id {request.data["card"]}.'
                return Response(
                    {'errors': error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except ValueError as error:
                return Response(
                    {'errors': str(error)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        else:
            return Response(
                {'errors': serializer.error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )
