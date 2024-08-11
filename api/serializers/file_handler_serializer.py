class FileHandlerSerializer:
    """
    FileHandlerSerializer - Uma classe para serializar e validar dados relacionados a manipulação de arquivos.

    Esta classe é projetada para ser usada em conjunto com solicitações HTTP, especialmente para upload de arquivos.
    """

    def __init__(self, request) -> None:
        """
        Inicializa um novo objeto FileHandlerSerializer.

        Parâmetros:
        - request: Um objeto de solicitação HTTP contendo dados relevantes.

        Atributos:
        - __file: Tupla contendo o arquivo enviado na solicitação.
        - __account: Tupla contendo informações da conta, se fornecido na solicitação.
        - __card: Tupla contendo informações do cartão, se fornecido na solicitação.
        - __user: O usuário associado à solicitação.
        - __error_message: Mensagem de erro, se a validação falhar.
        """
        self.__file = (request.FILES.get('file'),)
        self.__account = (request.data['account'],)
        self.__card = (request.data['card'],)
        self.__user = request.user
        self.__error_message = ''

    @property
    def file(self):
        """
        Obtém o arquivo associado à solicitação.

        Retorna:
        - Uma tupla contendo o arquivo enviado.
        """
        return self.__file

    @property
    def account(self):
        """
        Obtém as informações da conta associadas à solicitação.

        Retorna:
        - Uma tupla contendo as informações da conta.
        """
        return self.__account

    @property
    def card(self):
        """
        Obtém as informações do cartão associadas à solicitação.

        Retorna:
        - Uma tupla contendo as informações do cartão.
        """
        return self.__card

    @property
    def user(self):
        """
        Obtém o usuário associado à solicitação.

        Retorna:
        - O usuário associado à solicitação.
        """
        return self.__user

    @property
    def error_message(self):
        """
        Obtém a mensagem de erro, se a validação falhar.

        Retorna:
        - A mensagem de erro associada à validação.
        """
        return self.__error_message

    def is_valid(self):
        """
        Verifica se os dados na solicitação são válidos.

        Retorna:
        - True se os dados são válidos, False caso contrário.
        - Define __error_message com uma mensagem apropriada em caso de validação falha.
        """
        if not self.file[0]:
            self.__error_message = (
                'Era esperado receber um arquivo. Por favor, selecione um arquivo e tente novamente.'
            )
            return False
        elif not self.account[0] and not self.card[0]:
            self.__error_message = 'Era esperado receber uma conta ou um cartão. Por favor, selecione uma conta ou cartão e tente novamente.'
            return False
        elif not self.user:
            self.__error_message = (
                'Era esperado receber um usuário. Por favor, selecione um usuário e tente novamente.'
            )
        else:
            return True
