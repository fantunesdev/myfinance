from statement.models import Notification
from statement.services.base_service import BaseService

class NotificationService(BaseService):
    """ Serviço para gerenciar operações relacionadas ao modelo Notification. """

    model = Notification
