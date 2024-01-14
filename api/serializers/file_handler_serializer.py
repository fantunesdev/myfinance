class FileHandlerSerializer:
    def __init__(self, request) -> None:
        self.__file = (request.FILES.get('file'),)
        self.__account = (request.data['account'],)
        self.__card = (request.data['card'],)
        self.__user = request.user
        self.__error_message = ''

    @property
    def file(self):
        return self.__file

    @property
    def account(self):
        return self.__account

    @property
    def card(self):
        return self.__card

    @property
    def user(self):
        return self.__user

    @property
    def error_message(self):
        return self.__error_message

    def is_valid(self):
        """
        Valida o formulário recebido e lança mensagens de erro.

        Parameters:
        - request (django.http.HttpRequest) - Uma instância que contém
        informações sobre a solicitação, como parâmetros de consulta,
        cabeçalhos, método HTTP, dados do corpo, etc.

        Returns:
        bool: Se o formulário recebido é válido.
        """
        if not self.file[0]:
            self.__error_message = 'Era esperado receber um arquivo. Por favor, selecione um arquivo e tente novamente.'
            return False
        elif not self.account[0] and not self.card[0]:
            self.__error_message = 'Era esperado receber uma conta ou um cartão. Por favor, selecione uma conta ou cartão e tente novamente.'
            return False
        elif not self.user:
            self.__error_message = 'Era esperado receber um usuário. Por favor, selecione um usuário e tente novamente.'
        else:
            return True
