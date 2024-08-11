"""
Este módulo fornece serviços relacionados ao manuseio de arquivos.
Oferece funcionalidades para processar arquivos, incluindo a leitura de arquivos CSV e TXT
e a conversão de seu conteúdo em lançamentos."""

import csv
import json
import os
from json import JSONDecodeError

from django.conf import settings

from statement.services import account_services, card_services


class FileHandler:
    """Uma classe que processa arquivos, lê seu conteúdo e converte em lançamentos."""

    def __init__(self, request) -> None:
        """
        Inicializa a instância da classe FileHandler.

        Parameters:
        - request: O objeto de requisição Django contendo informações sobre o formulário e o arquivo.

        Initializes:
        - __file: O arquivo fornecido para processamento.
        - __account: A conta associada à requisição, se especificada.
        - __card: O cartão associado à requisição, se especificado.
        - __user: O usuário associado à requisição.
        - __extention: A extensão do arquivo.
        - __path: O caminho para o local onde o arquivo é salvo temporariamente.
        - __transactions: Uma lista vazia que armazenará os lançamentos extraídos do arquivo.
        - __error_message: Mensagem de erro, inicialmente vazia.
        - __file_conf: Um JSON com configuração da conta ou do cartão associado proveniente da instância da conta ou do cartão.

        Calls:
        - __handle_file(): Processa o arquivo, salvando, lendo e removendo
        """
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
        """
        Getter para a propriedade 'file'.

        Returns:
        O arquivo fornecido para processamento.
        """
        return self.__file

    @property
    def error_message(self):
        """
        Getter para a propriedade 'error_message'.

        Returns:
        A mensagem de erro associada ao processamento do arquivo.
        """
        return self.__error_message

    @property
    def account(self):
        """
        Obtém a instância da conta cadastrada no banco de dados com suas configurações.

        Returns:
        A conta associada à requisição, se especificada. Retorna None se não houver uma conta associada.
        """
        return self.__account

    @property
    def card(self):
        """
        Obtém a instância do cartão cadastrada no banco de dados com suas configurações.

        Returns:
        O cartão associada à requisição, se especificado. Retorna None se não houver um cartão associado.
        """
        return self.__card

    @property
    def extention(self):
        """
        Getter para a propriedade 'extention'.

        Returns:
        A extensão do arquivo em letras minúsculas.
        """
        return self.__extention

    @property
    def path(self):
        """
        Getter para a propriedade 'path'.

        Returns:
        O caminho para o local onde o arquivo é salvo temporariamente.
        """
        return self.__path

    @property
    def user(self):
        """
        Getter para a propriedade 'user'.

        Returns:
        O usuário associado ao arquivo.
        """
        return self.__user

    @property
    def file_conf(self):
        """
        Getter para a propriedade 'file_conf'.

        Returns:
        A configuração do manipulador de arquivo para a conta ou cartão associado.
        """
        return self.__file_conf

    @property
    def transactions(self):
        """
        Getter para a propriedade 'transactions'.

        Returns:
        Uma lista de lançamentos extraídos do arquivo.
        """
        return self.__transactions

    def __set_account(self, request):
        """
        Setter do atributo 'account' com a instância da conta associada à requisição, se especificada.

        Parameters:
        - request: O objeto de requisição Django contendo informações sobre o upload do arquivo.

        Returns:
        A instância da conta cadastrada no banco de dados com base no ID fornecido no request. Retorna None se não houver uma conta associada ou se ocorrer um erro durante a obtenção da conta.
        """
        try:
            account = request.data['account']
            user = request.user
            return account_services.get_account_by_id(account, user)
        except ValueError:
            return None

    def __set_card(self, request):
        """
        Setter do atributo 'card' com a instância do cartão associado à requisição, se especificada.

        Parameters:
        - request: O objeto de requisição Django contendo informações sobre o upload do arquivo.

        Returns:
        A instância do cartão cadastrado no banco de dados com base no ID fornecido no request. Retorna None se não houver um cartão associado ou se ocorrer um erro durante a obtenção do cartão.
        """
        try:
            card = request.data['card']
            user = request.user
            return card_services.get_card_by_id(card, user)
        except ValueError:
            return None

    def __set_extension(self, request):
        """
        Setter do atributo 'extension' que corresponde à extensão do arquivo fornecido no request.

        Parameters:
        - request: O objeto de requisição Django contendo informações sobre o upload do arquivo.

        Returns:
        A extensão do arquivo em letras minúsculas.
        """
        file = request.FILES.get('file')
        return file.name.split('.')[-1].lower()

    def __set_path(self, request):
        """
        Configura o caminho onde o arquivo será temporariamente salvo.

        Parameters:
        - request: O objeto de requisição Django contendo informações sobre o upload do arquivo.

        Returns:
        O caminho para o local onde o arquivo será salvo temporariamente.
        """
        upload_dir = f'{settings.MEDIA_ROOT}/uploads'
        if not os.path.exists(upload_dir):
            os.mkdir(upload_dir)
        file = request.FILES.get('file')
        return os.path.join(settings.MEDIA_ROOT, 'uploads', file.name)

    def __set_file_conf(self):
        """
        Valida se a propriedade 'file_handler_conf' está configurado para este cartão ou conta e atribui seu valor para a propriedade 'file_conf'.

        Raises:
        - JSONDecodeError: Se ocorrer um erro ao decodificar a propriedade 'file_handler_conf'.
        - ValueError: Se a propriedade 'file_handler_conf' não estiver configurada para a conta ou cartão associado.
        """
        try:
            if self.account:
                if self.account.file_handler_conf:
                    self.__file_conf = json.loads(self.account.file_handler_conf)
            if self.card:
                if self.card.file_handler_conf:
                    self.__file_conf = json.loads(self.card.file_handler_conf)
        except JSONDecodeError as message:
            self.__error_message = f'Erro ao ler a propriedade file_handler_conf: {message}.'
            raise ValueError(self.error_message)

        if not self.__file_conf:
            self.__error_message = 'A propriedade file_handler_conf desta conta não está configurada.'
            raise ValueError(self.error_message)

    def __handle_file(self):
        """
        Processa o arquivo, salvando, lendo e removendo.

        Calls:
        - __save_file(): Salva o arquivo temporariamente.
        - __read_file(): Lê o conteúdo do arquivo com base na sua extensão (CSV ou TXT).
        - __remove_file(): Remove o arquivo temporário após a leitura.

        Returns:
        O conteúdo do arquivo lido.
        """
        self.__save_file()
        content = self.__read_file()
        self.__remove_file()
        return content

    def __save_file(self):
        """
        Salva o arquivo temporariamente no caminho especificado.

        Raises:
        - IOError: Se ocorrer um erro ao salvar o arquivo.
        """
        with open(self.path, 'wb+') as destination:
            for chunk in self.__file.chunks():
                destination.write(chunk)

    def __read_file(self):
        """
        Lê o conteúdo do arquivo com base na sua extensão.

        Returns:
        O conteúdo do arquivo lido.

        Raises:
        - ValueError: Se a extensão do arquivo não for suportada.
        """
        match self.extention:
            case 'txt':
                with open(self.path, 'r') as file:
                    content = file.read()
                return content
            case 'csv':
                return self.__read_csv()

    def __remove_file(self):
        """
        Remove o arquivo temporário após a leitura.

        Raises:
        - FileNotFoundError: Se o arquivo não puder ser encontrado ou removido.
        """
        os.remove(self.path)

    def __read_csv(self):
        """
        Lê o conteúdo de um arquivo CSV e processa suas linhas para extrair os lançamentos.

        Raises:
        - ValueError: Se ocorrerem erros durante a leitura ou processamento do arquivo CSV.
        """
        with open(self.path, 'r', newline='', encoding='utf-8') as csv_file:
            self.__set_file_conf()

            first_row = csv_file.readline()
            first_row = first_row.replace('\n', '')

            if ',' in first_row:
                delimiter = ','
            elif ';' in first_row:
                delimiter = ';'
            else:
                self.__error_message = 'O arquivo não tem um delimitador válido ("," ou ";").'
                raise ValueError(self.error_message)

            reader = csv.reader(csv_file, delimiter=delimiter)
            file_header = first_row.split(delimiter)
            conf_header = self.__file_conf['header']
            header_size = len(conf_header)

            if header_size == 3:
                plus = 0
            elif header_size == 4:
                plus = 1
            else:
                self.__error_message = (
                    f'Tamanho de cabeçalho inválido: {header_size}. Tamanhos esperados: 3 e 4'
                )
                raise ValueError(self.error_message)

            if file_header == conf_header:
                for id, row in enumerate(reader):
                    if row:
                        print(row)
                        transaction = {
                            'id': id,
                            'date': self.__handle_date(row[0]),
                            'account': self.account.id if self.account else None,
                            'card': self.card.id if self.card else None,
                            'category': self.__handle_category(row[1]),
                            'subcategory': self.__handle_subcategory(row[1 + plus]),
                            'type': self.__handle_type(row[2 + plus]),
                            'description': self.__handle_description(row[1 + plus]),
                            'value': self.__handle_value(row[2 + plus]),
                        }
                        print(transaction)

                        if self.account:
                            del transaction['card']
                        else:
                            del transaction['account']

                        self.transactions.append(transaction)
                    else:
                        self.__error_message = (
                            'Arquivo com linha vazia. Remova a linha vazia e tente novamente'
                        )
                        raise ValueError(self.error_message)
            else:
                self.__error_message = (
                    f'O cabeçalho do arquivo é inválido: {file_header}. Cabeçalho esperado: {conf_header}.'
                )
                raise ValueError(self.error_message)

    def __handle_date(self, date):
        """
        Converte uma string de data no formato 'dd/mm/aaaa' ou 'aaaa-mm-dd' para o formato 'aaaa-mm-dd'.

        Parameters:
        - date: A string de data a ser processada.

        Returns:
        A string de data no formato 'aaaa-mm-dd'.
        """
        if '/' in date:
            day, month, year = date.split('/')
        elif '-' in date:
            day, month, year = date.split('-')
            if len(year) == 2:
                year, month, day = date.split('-')
        else:
            year = date[:4]
            month = date[5:6]
            day = date[6:]
        return f'{year}-{month}-{day}'

    def __handle_category(self, file_description):
        """
        Identifica a categoria associada a uma descrição de arquivo com base nas configurações da conta
        ou cartão (file_handler_conf).

        Parameters:
        - file_description: A descrição do arquivo a ser processada.

        Returns:
        O ID da categoria associada à descrição do arquivo, ou a primeira parte da descrição se
        nenhuma correspondência for encontrada.
        """

        # Para aproveitar o FOR, vamos cadastras as categorias na mensagem de erro
        self.__error_message = (
            f'Categoria não encontrada a partir da descrição: {file_description}. Categorias válidas: '
        )
        for category in self.file_conf['categories']:
            self.__error_message += f'{category["word"]}. '
            if category['word'] in file_description:
                return category['id']
        raise ValueError(self.error_message)

    def __handle_subcategory(self, file_description):
        """
        Identifica a subcategoria associada a uma descrição de arquivo com base nas configurações
        da conta ou cartão (file_handler_conf).

        Parameters:
        - file_description: A descrição do arquivo a ser processada.

        Returns:
        O ID da subcategoria associada à descrição do arquivo, ou a primeira parte da descrição se
        nenhuma correspondência for encontrada.
        """

        # Para aproveitar o FOR, vamos cadastras as subcategorias na mensagem de erro
        self.__error_message = (
            f'Subcategoria não encontrada a partir da descrição: {file_description}. Subtegorias válidas: '
        )
        for subcategory in self.file_conf['subcategories']:
            self.__error_message += f'{subcategory["word"]}. '
            if subcategory['word'] in file_description:
                return subcategory['id']
        raise ValueError(self.error_message)

    def __handle_type(self, value):
        """
        Determina o tipo de lançamento (entrada ou saída) com base no valor (positivo ou negativo)
        invertendo esses valores no caso do cartão.

        Parameters:
        - value: O valor da lançamento.

        Returns:
        Uma string indicando o tipo de lançamento: 'entrada' ou 'saida'.
        """
        if self.account:
            if value[0] == '-':
                return 'saida'
            return 'entrada'
        else:
            if value[0] == '-':
                return 'entrada'
            return 'saida'

    def __handle_description(self, file_description):
        """
        Processa a descrição do arquivo, aplicando regras de correspondência configuradas da conta ou do cartão (file_handler_conf).

        Parameters:
        - file_description: A descrição do arquivo a ser processada.

        Returns:
        A descrição processada conforme as regras de correspondência configuradas.
        """
        file_words = file_description.split()
        file_description = ' '.join(file_words)

        for description in self.file_conf['description']:
            if description['word'] in file_description:
                return file_description.split(description['delimiter'])[-1].upper()
        return file_description.split('-')[-1].title()

    def __handle_value(self, value):
        value = value.replace('.', ',')
        if value[0] == '-':
            return value[1:]
        return value
