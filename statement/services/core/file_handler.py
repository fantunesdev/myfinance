import csv

from clients.transaction_classifier.transaction_classifier import TransactionClassifierClient
from statement.services.core.account import AccountService
from statement.services.core.card import CardService
from statement.services.core.category import CategoryService


class FileHandlerService:
    """
    Classe responsável por manipular arquivos CSV e JSON.
    """

    def __init__(self, request):
        """
        Inicializa a classe com o request.

        :param request: Objeto de requisição do Django.
        """
        self._file = request.FILES.get('file')
        self._extension = self._file.name.split('.')[-1].lower()
        self._user = request.user
        self._account = self._set_account(request)
        self._card = self._set_card(request)

    def _set_account(self, request):
        """
        Define a conta associada ao arquivo.

        :param request: Objeto de requisição do Django.
        :return: Conta associada ao arquivo.
        """
        account_id = request.data['account']
        if account_id:
            return AccountService.get_by_id(account_id, user=self._user)
        return None

    def _set_card(self, request):
        """
        Define o cartão associado ao arquivo.

        :param request: Objeto de requisição do Django.
        :return: Cartão associado ao arquivo.
        """
        card_id = request.data['card']
        if card_id:
            return CardService.get_by_id(card_id, user=self._user)
        return None

    def read_file(self):
        """
        Lê o arquivo e retorna os dados processados.
        :return: Lista de dicionários com os dados do arquivo.
        """
        if self._extension == 'csv':
            return self._read_csv()
        raise ValueError('Unsupported file format. Only CSV and JSON are supported.')

    def _read_csv(self):
        """
        Lê um arquivo CSV e retorna os dados como uma lista de dicionários.

        :param description: Descrição do lançamento.
        :return: Lista de dicionários com os dados do arquivo CSV.
        """
        transactions = []
        reader = csv.DictReader(self._file.read().decode('utf-8').splitlines())
        for i, row in enumerate(reader):
            # Obtém a predição da categoria e da subcategoria a partir do micro serviço
            microservice_client = TransactionClassifierClient(self._user)
            predicted = microservice_client.predict(row['title'], row.get('category', ''))

            # Instancia a categoria predita para obter o tipo (entrada/saída)
            category = CategoryService.get_by_id(predicted['category_id'], user=self._user)
            transaction = {
                'id': i + 1,
                'date': row['date'],
                'type': category.type,
                'account': self._account.id if self._account else None,
                'card': self._card.id if self._card else None,
                'category': predicted['category_id'],
                'subcategory': predicted['subcategory_id'],
                'description': predicted['description'],
                'value': row['amount'],
            }
            transactions.append(transaction)
        if not transactions:
            raise ValueError('O arquivo está vazio.')
        return transactions
