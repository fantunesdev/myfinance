from clients.transaction_classifier.base_microservice import BaseMicroserviceClient
from clients.transaction_classifier.description_predictor import DescriptionPredictorClient
from clients.transaction_classifier.subcategory_predictor import SubcategoryPredictorClient
from statement.utils.datetime import DateTimeUtils
from statement.utils.utils import DictToObject


class TransactionClassifierClient(BaseMicroserviceClient):
    """
    Cliente para consumir o micro serviço Transaction Classifier
    """

    def __init__(self, user):
        super().__init__(user)
        self.subcategory = SubcategoryPredictorClient(user)
        self.description = DescriptionPredictorClient(user)

    def status(self):
        """
        Envia uma solicitação para o micro serviço para obter o status de treinamento do modelo do usuário.
        """
        response = self._send_requisition('status', 'get')
        self._handle_status_data(response)
        return response

    def predict(self, description: str, category: str = '', source_category: str = '', **context):
        """
        Faz uma previsão
        """
        predicted = {}
        predicted |= self.subcategory.predict(description, category, source_category, **context)
        predicted |= self.description.predict(description, **context)
        return predicted

    def start_job(self, job):
        return self._send_requisition(
            'jobs',
            'post',
            {
                'id': str(job.pk),
                'predictor': job.predictor,
                'operation': job.operation,
                'feedbacks': job.feedbacks,
                'callback_secret': job.secret,
            },
            timeout=(3, 8),
        )

    def job_status(self, job_id):
        return self._send_requisition(f'jobs/{job_id}', 'get', timeout=(2, 3))

    def _handle_status_data(self, response):
        """
        Transforma o dicionário da resposta do status em um objeto e realiza a conversão da data.

        :param response: dict - A resposta do micro serviço contendo as informações de status.
        :return: None - O método modifica a resposta diretamente, substituindo o valor da chave 'data'.
        """
        for i, _ in enumerate(response['data']):
            date = response['data'][i]['date']
            if date:
                response['data'][i]['date'] = DateTimeUtils.string_to_date(date)
            response['data'][i] = DictToObject(response['data'][i])
