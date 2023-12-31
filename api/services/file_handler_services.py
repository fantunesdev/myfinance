import csv
import os

from django.conf import settings

from statement.entities.transaction import Transaction
from statement.services import account_services


class FileHandler():
    def __init__(self, file, account, card, user) -> None:
        self.file = file
        self.account = account
        self.card = card
        self.user = user
        self.extention = file.name.split('.')[-1].lower()
        self.path = os.path.join(settings.MEDIA_ROOT, 'uploads', file.name)
        self.transactions = []
        self.__handle_file()

    def __handle_file(self):
        self.__save_file()
        content = self.__read_file()
        self.__remove_file()
        return content

    def __save_file(self):
        with open(self.path, 'wb+') as destination:
            for chunk in self.file.chunks():
                destination.write(chunk)

    def __read_file(self):
        match self.extention:
            case 'txt':
                with open(self.path, 'r') as file:
                    content = file.read()
                return content
            case 'csv':
                return self.__read_inter_csv()
        
    
    def __remove_file(self):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            print(f'Arquivo {self.file.name} não encontrado.')

    def __read_inter_csv(self):
        with open(self.path, 'r', newline='', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file, delimiter=';')

            ignore = True
            
            for id, row in enumerate(reader):
                try:
                    if row == self.inter_header:
                        ignore = False

                    if not ignore:
                        transaction = {
                            'id': id,
                            'date': self.__handle_date(row[0]),
                            'account': self.account,
                            'card': self.card,
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
        description = file_description.split('-')[0].rstrip()
        if 'PROV' in file_description:
            description = 'Provento'
        elif 'PAGAMENTO' in file_description:
            description = 'Pagamento de Título'
        elif 'VENCIMENTO' or 'RESGATE' in file_description:
            description = 'Resgate'
        return description
    
    def __handle_subcategory(self, file_description):
        description = file_description.split('-')[0].rstrip()
        if 'PAGAMENTO' in file_description:
            description = 'PAGAMENTO DE TÍTULO'
        return description.title()

    def __handle_description(self, description):
        words = description.split()
        description = ' '.join(words)
        if 'PROV' in description:
            description = description.split('*')[-1].lstrip()
            description = description[:-5].title() + description[-5:]
        elif 'RESGATE' or 'VENCIMENTO' in description:
            description = description.split('-')[-1].lstrip().title()
        elif 'PAGAMENTO' in description:
            description = 'Boleto'
        return description

    def __handle_type(self, value):
        if value[0] == '-':
            return 'saida'
        return 'entrada'
    
    def __handle_value(self, value):
        if value[0] == '-':
            return value[1:]
        return value
                

    inter_header = ['Data Lançamento', 'Descrição', 'Valor', 'Saldo']
