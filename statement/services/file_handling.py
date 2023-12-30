import csv
import os

from django.conf import settings

from statement.entities.transaction import Transaction
from statement.services import account_services


class FileHandling():
    def __init__(self, file, user) -> None:
        self.file = file
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
            print(f'Arquivo {self.file.name} removido.')
        except FileNotFoundError:
            print(f'Arquivo {self.file.name} não encontrado.')

    def __read_inter_csv(self):
        with open(self.path, 'r', newline='', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file, delimiter=';')

            ignore = True

            try:
                next(reader, None)
                account_number = int(next(reader, None)[1])
                account = account_services.get_account_by_account_number(account_number, self.user)
            except ValueError:
                account_number = None
            
            for row in reader:
                try:
                    if row == self.inter_header:
                        ignore = False

                    if not ignore:
                        day, month, year = row[0].split('/')
                        transaction = Transaction(
                            payment_date=f'{year}-{month}-{day}',
                            release_date=f'{year}-{month}-{day}',
                            account=account,
                            card=None,
                            category=None,
                            subcategory=None,
                            description=(' '.join(row[1].split())).title(),
                            value=row[2],
                            installments_number=None,
                            paid=None,
                            fixed=None,
                            annual=None,
                            currency='BRL',
                            observation=None,
                            remember=None,
                            type='saida' if row[2][0] == '1' else 'entrada',
                            effected=None,
                            home_screen=None,
                            user=self.user,
                            installment=None
                        )
                        self.transactions.append(transaction)
                except IndexError:
                    pass
                except ValueError:
                    pass
                

    inter_header = ['Data Lançamento', 'Descrição', 'Valor', 'Saldo']
