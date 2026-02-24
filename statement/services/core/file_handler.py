import csv
import json
import re

from datetime import datetime
from clients.transaction_classifier.transaction_classifier import TransactionClassifierClient
from statement.models import AppConfig
from statement.services.core.account import AccountService
from statement.services.core.card import CardService
from statement.services.core.category import CategoryService
from statement.services.core.notification import NotificationService


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

    def read_file(self, file_type='csv'):
        """
        Lê o arquivo e retorna os dados processados.
        
        :param file_type: Tipo de arquivo ('csv' ou 'tasker_json')
        :return: Lista de dicionários com os dados do arquivo.
        """
        if file_type == 'tasker_json':
            return self._read_tasker_json()
        elif file_type == 'csv':
            return self._read_csv()
        raise ValueError('Unsupported file format. Only CSV and Tasker JSON are supported.')

    def _read_csv(self):
        """
        Lê um arquivo CSV e retorna os dados como uma lista de dicionários.

        :param description: Descrição do lançamento.
        :return: Lista de dicionários com os dados do arquivo CSV.
        """
        transactions = []
        reader = csv.DictReader(self._file.read().decode('utf-8').splitlines())
        for i, row in enumerate(reader):
            predicted = {
                'category_id': None,
                'subcategory_id': None,
                'description': row['title'],
            }

            # Only call classifier if global toggle enabled
            try:
                if AppConfig.get_solo().enable_transaction_classifier:
                    microservice_client = TransactionClassifierClient(self._user)
                    predicted = microservice_client.predict(row['title'], row.get('category', ''))
            except Exception:
                # On any failure, fallback to original values
                predicted = {
                    'category_id': None,
                    'subcategory_id': None,
                    'description': row['title'],
                }

            # If classifier returned a category id, instantiate to obtain type (entrada/saída)
            category = None
            if predicted.get('category_id'):
                try:
                    category = CategoryService.get_by_id(predicted['category_id'], user=self._user)
                except Exception:
                    category = None
            transaction = {
                'id': i + 1,
                'date': row['date'],
                'type': category.type if category else 'saida',
                'account': self._account.id if self._account else None,
                'card': self._card.id if self._card else None,
                'category': predicted['category_id'],
                'subcategory': predicted['subcategory_id'],
                'description': predicted['description'],
                'original_description': row.get('title') or row.get('description') or '',
                'value': row['amount'],
            }
            transactions.append(transaction)
        if not transactions:
            raise ValueError('O arquivo está vazio.')
        return transactions
    def _read_tasker_json(self):
        """
        Lê um arquivo JSON do Tasker (uma linha por JSON) e converte em notificações.
        
        Formato esperado (JSON Lines - um JSON por linha):
        {
            "app": "br.com.intermedium",
            "title": "Compra no crédito",
            "message": "Mensagem completa...",
            "date": "2026-02-06 14:26:55"
        }
        
        :return: Lista de dicionários com os dados convertidos em notificações.
        """
        notifications_to_create = []
        file_content = self._file.read().decode('utf-8')
        # Obtém títulos habilitados, se o modelo existir e a query funcionar.
        try:
            from statement.services.core.notification_title import NotificationTitleService

            enabled_titles = NotificationTitleService.get_enabled_titles_for_user(self._user)
        except Exception:
            # Se houver qualquer problema (migrações não aplicadas, tabela ausente, etc.),
            # não filtramos por título para evitar interromper o fluxo de importação.
            enabled_titles = None
        
        for line_num, line in enumerate(file_content.splitlines(), 1):
            line = self._sanitize_utf8mb3(line)
            if not line.strip():
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f'Erro ao processar JSON na linha {line_num}: {str(e)}')
            
            # Valida os campos obrigatórios
            required_fields = ['app', 'title', 'message', 'date']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f'Campo obrigatório "{field}" não encontrado na linha {line_num}')

            # Se houver uma lista de títulos habilitados, pula notificações cujo título
            # não esteja habilitado nas configurações do usuário.
            if enabled_titles is not None and data['title'] not in enabled_titles:
                continue
            
            # Verifica se a notificação já existe (evita duplicata)
            existing = NotificationService.get_by_filter(
                app=data['app'],
                title=data['title'],
                message=data['message']
            )
            
            if existing.exists():
                continue  # Pula notificações duplicadas
            
            # Extrai o valor da mensagem se possível
            value = self._extract_value_from_message(data['message'])
            
            notifications_to_create.append({
                'app': data['app'],
                'title': data['title'],
                'message': data['message'],
                'date': data['date'],
                'value': value,
            })
        
        if not notifications_to_create:
            raise ValueError('Nenhuma notificação válida encontrada no arquivo.')
        
        return notifications_to_create

    def _extract_value_from_message(self, message):
        """
        Extrai o valor monetário da mensagem de notificação.
        
        Exemplo: "Você acaba de comprar R$ 69,71 em JACOMAR"
        Retorna: "69.71"
        
        :param message: Texto da mensagem.
        :return: Valor extraído ou None.
        """
        import re
        
        # Procura por padrão "R$ XX,XX"
        match = re.search(r'R\$\s*([\d.,]+)', message)
        if match:
            value_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                return float(value_str)
            except ValueError:
                return None
        
        return None

    def _sanitize_utf8mb3(self, text: str):
        if not isinstance(text, str):
            return text
        return re.sub(r'[\U00010000-\U0010FFFF]', '', text)
