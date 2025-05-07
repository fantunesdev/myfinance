import os
import requests
from typing import Union

from statement.utils.jwt import JWTUtils

class BaseMicroserviceClient:
    """ Classe base do microservi;o """

    BASE_URL = os.getenv('TRANSACTION_CLASSIFIER_URL')
    PORT = os.getenv('TRANSACTION_CLASSIFIER_PORT')
    request_method = {
        'get': requests.get,
        'post': requests.post,
    }

    def __init__(self, user):
        self._token = JWTUtils.generate_access_token_for_user(user)
        self._base_url = f'{self.BASE_URL}:{self.PORT}'
        self._headers = {'Authorization': f'Bearer {self._token}'}

    def _send_requisition(self, endpoint: str, method: str, body: Union[str, dict] = ''):
        """
        Método que envia requisições para o micro serviço.

        :param endpoint: O endpoint da requisição no micro serviço.
        :param body: Um json com o corpo da requisição serializado.
        """
        url = f'{self._base_url}/{endpoint}'
        response = self.request_method[method](url, headers=self._headers, json=body, timeout=20)
        response.raise_for_status()
        return response.json()
