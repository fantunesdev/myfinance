from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.serializers.transaction import TransactionSerializer
from api.views.base_view import BaseView
from statement.models import Transaction
from statement.services.core.account import AccountService
from statement.services.core.card import CardService
from statement.services.core.file_handler import FileHandlerService
from statement.services.core.transaction import TransactionService
from statement.views.core.transaction import TransactionView as StatementView


class TransactionView(BaseView):
    """
    Classe que gerencia a view das categorias na API.
    """

    model = Transaction
    service = TransactionService
    serializer = TransactionSerializer
    statement_view = StatementView

    @action(detail=False, methods=['get'], url_path='year/(?P<year>\d{4})')
    def get_by_year(self, request, year):
        """
        Obtém os lançamentos por ano.
        """
        return self._get_transactions_by_date(request, year=year)

    @action(detail=False, methods=['get'], url_path='year/(?P<year>\d{4})/month/(?P<month>\d{1,2})')
    def get_by_year_and_month(self, request, year, month):
        """
        Obtém os lançamentos por ano e mês.
        """
        return self._get_transactions_by_date(request, year=year, month=month)

    @action(detail=False, methods=['get'], url_path='accounts/(?P<account_id>\d+)/year/(?P<year>\d{4})/month/(?P<month>\d{1,2})')
    def get_extract_by_year_and_month(self, request, account_id, year, month):
        """
        Obtém os lançamentos por conta, ano e mês.
        """
        return self._get_transactions_by_date(request, account=account_id, year=year, month=month)

    @action(detail=False, methods=['get'], url_path='cards/(?P<card_id>\d+)/year/(?P<year>\d{4})/month/(?P<month>\d{1,2})')
    def get_invoice_by_year_and_month(self, request, card_id, year, month):
        """
        Obtém os lançamentos por conta, ano e mês.
        """
        return self._get_transactions_by_date(request, card=card_id, year=year, month=month)

    def _get_transactions_by_date(self, request, account=None, card=None, year=None, month=None):
        """
        Método auxiliar para obter transações por data.
        """
        kwargs = {
            'user': request.user,
            'payment_date__year': year
        }

        if month:
            kwargs['payment_date__month'] = month
        if account:
            kwargs['account'] = AccountService.get_by_id(account)
        if card:
            kwargs['card'] = CardService.get_by_id(card)

        transactions = TransactionService.get_by_filter(**kwargs)

        if not transactions:
            message = 'Lançamentos não encontrados.'
            return Response({'detail': message}, status=status.HTTP_404_NOT_FOUND)

        return self._serialize_and_return(transactions)

    @action(detail=False, methods=['post'], url_path='import')
    def import_transactions(self, request):
        """
        Método para importar transações.
        """
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'Arquivo não encontrado.'}, status=status.HTTP_400_BAD_REQUEST)

        file_handler = FileHandlerService(request)
        transactions = file_handler.read_file()

        if not transactions:
            return Response({'detail': 'Nenhum lançamento encontrado no arquivo.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(transactions, status=status.HTTP_200_OK)
