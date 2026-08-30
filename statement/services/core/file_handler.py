import csv
import json
import re
from decimal import Decimal, InvalidOperation

from django.db.models import Q

from clients.transaction_classifier.transaction_classifier import TransactionClassifierClient
from statement.models import AppConfig, CSVImportConfig, Transaction
from statement.services.core.account import AccountService
from statement.services.core.card import CardService
from statement.services.core.category import CategoryService
from statement.services.core.notification import NotificationService
from statement.utils.text import sanitize_utf8mb3


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
        self._csv_config = self._set_csv_config(request)
        self._account = self._set_account(request)
        self._card = self._set_card(request)
        self._is_configurable_csv = request.data.get('csv_mode') == 'configurable' or bool(self._csv_config)
        self._target_model = (
            self._csv_config.target_model
            if self._csv_config
            else request.data.get('target_model', 'statement_transaction')
            if self._is_configurable_csv
            else 'statement_transaction'
        )
        self._date_column = self._get_configured_value(request, 'date_column', 'date')
        self._description_column = self._get_configured_value(request, 'description_column', 'title')
        self._value_column = self._get_configured_value(request, 'value_column', 'amount')
        self._installment_column = self._get_configured_value(request, 'installment_column', '')
        self._installment_format = self._get_configured_value(request, 'installment_format', 'auto') or 'auto'
        self._date_column = self._normalize_csv_header(self._date_column or 'date')
        self._description_column = self._normalize_csv_header(self._description_column or 'title')
        self._value_column = self._normalize_csv_header(self._value_column or 'amount')
        self._installment_column = self._normalize_csv_header(self._installment_column or '')
        self._matching_fields = self._set_matching_fields(request)

    def _set_csv_config(self, request):
        config_id = request.data.get('csv_import_config') or request.data.get('csv_import_config_id')
        if not config_id:
            return None
        return CSVImportConfig.objects.get(id=config_id, user=self._user)

    def _get_configured_value(self, request, field_name, default):
        if not self._is_configurable_csv:
            return default
        if self._csv_config:
            return getattr(self._csv_config, field_name)
        return request.data.get(field_name)

    def _set_matching_fields(self, request):
        if self._csv_config:
            return self._csv_config.matching_fields or []
        raw_fields = request.data.get('matching_fields', '')
        if isinstance(raw_fields, str):
            return [field for field in raw_fields.split(',') if field]
        return raw_fields or []

    def _set_account(self, request):
        """
        Define a conta associada ao arquivo.

        :param request: Objeto de requisição do Django.
        :return: Conta associada ao arquivo.
        """
        account_id = self._csv_config.account_id if self._csv_config else request.data['account']
        if account_id:
            return AccountService.get_by_id(account_id, user=self._user)
        return None

    def _set_card(self, request):
        """
        Define o cartão associado ao arquivo.

        :param request: Objeto de requisição do Django.
        :return: Cartão associado ao arquivo.
        """
        card_id = self._csv_config.card_id if self._csv_config else request.data['card']
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
        file_content = self._file.read().decode('utf-8-sig')
        reader = self._get_csv_reader(file_content)
        for i, row in enumerate(reader, start=1):
            row = self._normalize_csv_row(row)
            self._validate_csv_columns(row, i)
            date = row[self._date_column]
            description = row[self._description_column]
            installment_text = self._extract_installment_text(row)
            installment_paid, installments_number = self._parse_installment_numbers(installment_text)
            value = (
                self._normalize_value(row[self._value_column])
                if self._is_configurable_csv
                else row[self._value_column]
            )

            if self._target_model in ('investment_transaction', 'investments_investmenttransaction'):
                transactions.append(
                    {
                        'id': i + 1,
                        'target_model': self._target_model,
                        'date': date,
                        'description': description,
                        'original_description': description,
                        'installment_text': installment_text,
                        'paid': installment_paid,
                        'installments_number': installments_number,
                        'value': value,
                    }
                )
                continue

            predicted = {
                'category_id': None,
                'subcategory_id': None,
                'description': description,
            }

            # Only call classifier if global toggle enabled
            try:
                if AppConfig.get_solo().enable_transaction_classifier:
                    microservice_client = TransactionClassifierClient(self._user)
                    predicted = microservice_client.predict(description, row.get('category', ''))
            except Exception:
                # On any failure, fallback to original values
                predicted = {
                    'category_id': None,
                    'subcategory_id': None,
                    'description': description,
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
                'target_model': self._target_model,
                'date': date,
                'type': category.type if category else 'saida',
                'account': self._account.id if self._account else None,
                'card': self._card.id if self._card else None,
                'category': predicted['category_id'],
                'subcategory': predicted['subcategory_id'],
                'description': predicted['description'],
                'original_description': description,
                'installment_text': installment_text,
                'paid': installment_paid,
                'installments_number': installments_number,
                'value': value,
                'matching_fields': self._matching_fields,
            }
            duplicate = self._find_duplicate_transaction(transaction)
            transaction.update(
                {
                    'is_duplicate': duplicate is not None,
                    'duplicate_id': duplicate.id if duplicate else None,
                }
            )
            transactions.append(transaction)
        if not transactions:
            raise ValueError('O arquivo está vazio.')
        return transactions

    def _get_csv_reader(self, file_content):
        lines = file_content.splitlines()
        try:
            dialect = csv.Sniffer().sniff(file_content[:2048], delimiters=',;')
            return csv.DictReader(lines, dialect=dialect)
        except csv.Error:
            return csv.DictReader(lines)

    def _validate_csv_columns(self, row, line_number):
        required_columns = [self._date_column, self._description_column, self._value_column]
        if self._installment_column:
            required_columns.append(self._installment_column)

        missing_columns = [
            column
            for column in required_columns
            if column not in row
        ]
        if missing_columns:
            columns = ', '.join(missing_columns)
            raise ValueError(f'Coluna(s) não encontrada(s) no CSV na linha {line_number}: {columns}')

    def _normalize_csv_row(self, row):
        return {self._normalize_csv_header(key): value for key, value in row.items() if key is not None}

    def _normalize_csv_header(self, header):
        if header is None:
            return ''
        return str(header).replace('\ufeff', '').strip().strip('"').strip("'").strip()

    def _extract_installment_text(self, row):
        if not self._installment_column:
            return ''
        if self._installment_column not in row:
            return ''
        raw_value = row.get(self._installment_column) or ''
        return self._parse_installment_text(raw_value)

    def _parse_installment_text(self, value):
        value = str(value).strip()
        if not value:
            return ''

        patterns = {
            'slash': r'(\d+)\s*/\s*(\d+)',
            'dash': r'(\d+)\s*-\s*(\d+)',
            'auto': r'(\d+)\s*[/\-]\s*(\d+)',
        }
        match = re.search(patterns.get(self._installment_format, patterns['auto']), value, re.IGNORECASE)
        if not match:
            return ''
        return f'{int(match.group(1))}/{int(match.group(2))}'

    def _parse_installment_numbers(self, installment_text):
        if not installment_text:
            return 0, 0
        match = re.search(r'(\d+)\s*/\s*(\d+)', installment_text)
        if not match:
            return 0, 0
        return int(match.group(1)), int(match.group(2))

    def _normalize_value(self, value):
        if value is None:
            return ''

        value = str(value).strip().replace('R$', '').replace(' ', '').replace('\xa0', '')
        if ',' in value and '.' in value:
            value = value.replace('.', '').replace(',', '.')
        elif ',' in value:
            value = value.replace(',', '.')

        try:
            return str(Decimal(value).quantize(Decimal('0.01')))
        except (InvalidOperation, ValueError):
            return value

    def _find_duplicate_transaction(self, transaction):
        installment_duplicate = self._find_installment_duplicate(transaction)
        if installment_duplicate:
            return installment_duplicate

        if not self._matching_fields:
            return None

        filters = {'user': self._user}
        if self._account:
            filters['account'] = self._account
        if self._card:
            filters['card'] = self._card

        for field in self._matching_fields:
            field_filter = self._build_duplicate_filter(field, transaction)
            if field_filter is None:
                return None
            filters.update(field_filter)

        return Transaction.objects.filter(**filters).first()

    def _find_installment_duplicate(self, transaction):
        if not transaction.get('installments_number'):
            return None

        posted_date = self._normalize_date(transaction.get('date'))
        if not posted_date:
            return None

        filters = {
            'user': self._user,
            'posted_date': posted_date,
            'paid': transaction.get('paid') or 1,
            'installments_number': transaction.get('installments_number'),
        }
        if self._account:
            filters['account'] = self._account
        transactions = Transaction.objects.filter(**filters)
        if self._card:
            transactions = transactions.filter(Q(card=self._card) | Q(card_number__card=self._card))

        matching_fields = self._get_installment_disambiguator_fields()
        if matching_fields:
            narrowed_transactions = self._narrow_installment_duplicates(transactions, transaction, matching_fields)
            if narrowed_transactions is None:
                return None
            candidates = list(narrowed_transactions[:2])
            return candidates[0] if len(candidates) == 1 else None

        candidates = list(transactions[:2])
        if len(candidates) == 1:
            return candidates[0]
        return None

    def _get_installment_disambiguator_fields(self):
        ignored_fields = {'posted_date', 'account', 'card', 'card_number'}
        return [field for field in self._matching_fields if field not in ignored_fields]

    def _narrow_installment_duplicates(self, transactions, transaction, matching_fields):
        for field in matching_fields:
            field_filter = self._build_duplicate_filter(field, transaction)
            if field_filter is None:
                return None
            transactions = transactions.filter(**field_filter)
        return transactions

    def _build_duplicate_filter(self, field, transaction):
        match field:
            case 'posted_date':
                date_value = self._normalize_date(transaction.get('date'))
                return {'posted_date': date_value} if date_value else None
            case 'description':
                return {'description': transaction.get('description') or ''}
            case 'original_description':
                return {'original_description': transaction.get('original_description') or ''}
            case 'value':
                try:
                    return {'value': float(transaction.get('value'))}
                except (TypeError, ValueError):
                    return None
            case 'account':
                return {'account': self._account} if self._account else {'account__isnull': True}
            case 'card':
                return {'card': self._card} if self._card else {'card__isnull': True}
            case 'card_number':
                return None
            case 'category':
                return {'category_id': transaction.get('category')} if transaction.get('category') else None
            case 'subcategory':
                return {'subcategory_id': transaction.get('subcategory')} if transaction.get('subcategory') else None
            case 'type':
                return {'type': transaction.get('type') or 'saida'}
            case _:
                return None

    def _normalize_date(self, value):
        if not value:
            return None
        value = str(value).strip()
        for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
            try:
                from datetime import datetime

                return datetime.strptime(value[:10], fmt).date()
            except ValueError:
                continue
        try:
            from dateutil.parser import parse

            return parse(value).date()
        except Exception:
            return None

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
            line = sanitize_utf8mb3(line)
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
            existing = NotificationService.get_by_filter(app=data['app'], title=data['title'], message=data['message'])

            if existing.exists():
                continue  # Pula notificações duplicadas

            # Extrai o valor da mensagem se possível
            value = self._extract_value_from_message(data['message'])

            notifications_to_create.append(
                {
                    'app': data['app'],
                    'title': data['title'],
                    'message': data['message'],
                    'date': data['date'],
                    'value': value,
                }
            )

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
