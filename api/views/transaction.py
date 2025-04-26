import logging
import re

import requests
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.serializers.base_serializer import BaseSerializer
from api.serializers.transaction import TransactionSerializer
from api.views.base_view import BaseView
from statement.models import Transaction
from statement.services.core.account import AccountService
from statement.services.core.card import CardService
from statement.services.core.category import CategoryService
from statement.services.core.file_handler import FileHandlerService
from statement.services.core.installment import InstallmentService
from statement.services.core.transaction import TransactionService
from statement.utils.datetime import DateTimeUtils
from statement.views.core.transaction import TransactionView as StatementView

logger = logging.getLogger('myfinance')


class TransactionView(BaseView):
    """
    Classe que gerencia a view das categorias na API.
    """

    model = Transaction
    service = TransactionService
    serializer = TransactionSerializer
    statement_view = StatementView
    installment_info = None

    def create(self, request):
        description = request.data.get('description')
        self._get_installments_number(description)

        # Se for um parcelamento, mas não for a primeira parcela, a parcela já foi cadastrada anteriormente.
        if self._is_installment_but_not_first():
            return Response({'detail': 'Parcela já cadastrada'}, status=status.HTTP_200_OK)

        self._process_transaction_request(request)

        result = super().create(request)

        if self.installment_info:
            return self._handle_installment_creation(result)

        return result

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

    def _is_installment_but_not_first(self):
        """
        Método auxiliar para verificar se a transação não é a primeira parcela.

        :return: True se não for a primeira parcela, False caso contrário.
        """
        try:
            return int(self.installment_info.group(0)) == 1
        except (ValueError, AttributeError):
            return False

    def _process_transaction_request(self, request):
        """
        Método que complementa a requisição com os dados necessários do model Transaction.

        :param request: Requisição da API.
        :return: Não retorna nada, pois request.data é atualizado diretamente no objeto request.
        """
        description = request.data.get('description')
        request.data['description'] = self._clean_description(description)

        # Monta um dicionário com atributos obrigatórios para o model Transaction
        request.data.update(
            {
                'user': request.user.id,
                'installments_number': self._get_installments_number(description),
                'paid': 0,
                'currency': 'BRL',
                'type': CategoryService.get_by_id(request.data.get('category')).type,
            }
        )

        # Se o lançamento for em uma conta, seta os campos necessários para o processamento
        if request.data.get('account'):
            request.data['account'] = AccountService.get_by_id(request.data.get('account'))
            request.data['payment_date'] = request.data.get('release_date')

        # Se o lançamento for em um cartão, seta os campos necessários para o processamento
        if request.data.get('card'):
            card = CardService.get_by_id(request.data.get('card'))
            date = DateTimeUtils.string_to_date(request.data.get('release_date'))
            payment_date = CardService.set_processing_date(card, date)

            request.data.update(
                {
                    'card': card.id,
                    'payment_date': payment_date.strftime('%Y-%m-%d'),
                }
            )

        # Se for a primeira parcela de um parcelamento, atualiza o valor para o valor total.
        # O valor da parcela será dividido igualmente dentro de InstallmentService.create(),
        # mais especificamente no método _set_transaction_value(), dentro de _set_first_installment()
        if self.installment_info:
            try:
                installment_number = int(self.installment_info.group(0).split('/')[0])
                if installment_number == 1:
                    value = float(request.data.get('value', 0))
                    installments_number = int(request.data.get('installments_number'))
                    request.data['value'] = value * installments_number
            except (ValueError, AttributeError):
                pass

    def _handle_installment_creation(self, result):
        """
        Método auxiliar para criar o parcelamento.

        :param result: Resultado da primeira parcela cadastrada no banco.
        :return: Resposta da API com os dados do parcelamento criado.
        """
        transaction = TransactionService.get_by_id(result.data.get('id'))
        installment = InstallmentService.create(
            form=None,
            user=transaction.user,
            transaction=transaction,
        )
        serializer = BaseSerializer(installment, model=InstallmentService.model)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _get_installments_number(self, description):
        """
        Método auxiliar para obter o número de parcelas.

        :param description: Descrição do lançamento.
        :return: Número de parcelas.
        """
        installment_match = re.search(r'(\d+/\d+)', description)

        # Se não for encontrado o padrão 1/10 (parcela/numero_de_parcelas), retorna 0
        if not installment_match:
            return 0

        installments_tag = installment_match.group(0)
        self.installment_info = installment_match

        return installments_tag.split('/')[1]

    def _clean_description(self, description):
        """
        Método auxiliar para limpar a descrição do lançamento.

        :param description: Descrição do lançamento.
        :return: Descrição limpa.
        """
        # Se não há match para a parcela, retorna a descrição original
        if not self.installment_info:
            return description

        # Remove a installment_info do final da descrição (Exemplo: "Parcela 1/3")
        description = description.replace(f' {self.installment_info.group(0)}', '')

        # Remove palavras de parcela junto com separador opcional após (como '-', ':', etc.)
        keywords = ['parcela', 'parc']
        pattern = r'\b(?:' + '|'.join(keywords) + r')\b[\s\-:–—]*'
        description = re.sub(pattern, '', description, flags=re.IGNORECASE)

        # Remove múltiplos espaços e pontuação solta no final
        return re.sub(r'\s+', ' ', description).strip(' -–—:')

    def _get_transactions_by_date(self, request, account=None, card=None, year=None, month=None):
        """
        Método auxiliar para obter transações por data.
        """
        kwargs = {'user': request.user, 'payment_date__year': year}

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

        try:
            file_handler = FileHandlerService(request)
            transactions = file_handler.read_file()
            return Response(transactions, status=status.HTTP_200_OK)
        except requests.exceptions.JSONDecodeError as e:
            logger.warning('Erro na conversão para JSON: %s', e)
            return Response({'errors': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except requests.exceptions.RequestException as e:
            logger.warning('Erro na requisição ao transaction_classifier: %s', e)
            return Response({'errors': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:  # pylint: disable=broad-except
            return Response({'errors': str(e)}, status=status.HTTP_400_BAD_REQUEST)
