import csv
import json
import os

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from statement.entities.transaction import Transaction
from statement.services import account_services, card_services


class FileHandler():
    def __init__(self, request) -> None:
        self.__file = request.FILES.get('file')
        self.__account = self.__set_account(request)
        self.__card = self.__set_card(request)
        self.__user = request.user
        self.__extention = self.__set_extension(request)
        self.__path = self.__set_path(request)
        self.__transactions = []
        self.__error_message = ''
        self.__file_conf = None
        self.__handle_file()

    @property
    def file(self):
        return self.__file

    @property
    def error_message(self):
        return self.__error_message

    @property
    def account(self):
        return self.__account

    @property
    def card(self):
        return self.__card

    @property
    def extention(self):
        return self.__extention

    @property
    def path(self):
        return self.__path

    @property
    def user(self):
        return self.__user

    @property
    def file_conf(self):
        return self.__file_conf

    @property
    def transactions(self):
        return self.__transactions

    def __set_account(self, request):
        try:
            account = request.data['account']
            user = request.user
            return account_services.get_account_by_id(account, user)
        except ValueError:
            return None

    def __set_card(self, request):
        try:
            card = request.data['card']
            user = request.user
            return card_services.get_card_by_id(card, user)
        except ValueError:
            return None
        
    def __set_extension(self, request):
        file = request.FILES.get('file')
        return file.name.split('.')[-1].lower()
        
    def __set_path(self, request):
        file = request.FILES.get('file')
        return os.path.join(settings.MEDIA_ROOT, 'uploads', file.name)

    def __handle_file(self):
        self.__save_file()
        content = self.__read_file()
        self.__remove_file()
        return content

    def __save_file(self):
        with open(self.path, 'wb+') as destination:
            for chunk in self.__file.chunks():
                destination.write(chunk)

    def __read_file(self):
        match self.extention:
            case 'txt':
                with open(self.path, 'r') as file:
                    content = file.read()
                return content
            case 'csv':
                return self.__read_csv()
        
    
    def __remove_file(self):
        os.remove(self.path)

    def __read_csv(self):
        with open(self.path, 'r', newline='', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file, delimiter=';')

            self.__file_conf = json.loads(self.account.file_handler_conf)

            ignore = True
            
            for id, row in enumerate(reader):
                try:
                    if row == self.file_conf['header']:
                        ignore = False

                    if not ignore:
                        transaction = {
                            'id': id,
                            'date': self.__handle_date(row[0]),
                            'account': self.account.id if self.account else None,
                            'card': self.card.id if self.card else None,
                            'category': self.__handle_category(row[1]),
                            'subcategory': self.__handle_subcategory(row[1]),
                            'type': self.__handle_type(row[2]),
                            'description': self.__handle_description(row[1]),
                            'value': self.__handle_value(row[2])
                        }

                        if self.account:
                            del transaction['card']
                        else:
                            del transaction['account']
                        
                        self.transactions.append(transaction)
                except IndexError:
                    pass
                except ValueError:
                    pass

    def __handle_date(self, date):
        day, month, year = date.split('/')
        return f'{year}-{month}-{day}'
    
    def __handle_category(self, file_description):
        for category in self.file_conf['categories']:
            if category['word'] in file_description:
                return category['id']
        return file_description.split('-')[0].rstrip()
    
    def __handle_subcategory(self, file_description):
        for subcategory in self.file_conf['subcategories']:
            if subcategory['word'] in file_description:
                return subcategory['id']
        return file_description.split('-')[0].rstrip()

    def __handle_type(self, value):
        if value[0] == '-':
            return 'saida'
        return 'entrada'

    def __handle_description(self, file_description):
        file_words = file_description.split()
        file_description = ' '.join(file_words)
        
        for description in self.file_conf['description']:
            if description['word'] in file_description:
                return file_description.split(description['delimiter'])[-1].upper()
        return file_description.split('-')[-1].title()
    
    def __handle_value(self, value):
        if value[0] == '-':
            return value[1:]
        return value
