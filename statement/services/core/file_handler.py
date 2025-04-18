import csv
import os
from json.decoder import JSONDecodeError

import requests

from statement.services.core.account import AccountService
from statement.services.core.card import CardService
from statement.services.core.category import CategoryService
from statement.utils.jwt import JWTUtils


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
        self._token = JWTUtils.generate_token(self._user)

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
            predicted = self._predict(row)
            category = CategoryService.get_by_id(predicted['category_id'], user=self._user)
            transaction = {
                'id': i + 1,
                'date': row['date'],
                'type': category.type,
                'account': self._account.id if self._account else None,
                'card': self._card.id if self._card else None,
                'category': predicted['category_id'],
                'subcategory': predicted['subcategory_id'],
                'description': row['title'],
                'value': row['amount'],
            }
            transactions.append(transaction)
        if not transactions:
            raise ValueError('O arquivo está vazio.')
        return transactions

    def _predict(self, row):
        """
        Obtém a subcategoria associada ao lançamento.

        :param row: linha processada.
        :return: Subcategoria associada ao lançamento.
        """
        # TODO - O .env está ficando com muita responsabilidade.
        # Repensar o que está hoje no .env e deve ser transformado numa configuração.
        uri = os.getenv('TRANSACTION_CLASSIFIER_URL')
        port = os.getenv('TRANSACTION_CLASSIFIER_PORT')
        endpoint = f'predict/{self._user.id}'

        url = f'{uri}:{port}/{endpoint}'

        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {self._token}'}
        payload = {
            'description': row['title'],
            'category': row.get('category', None),
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
