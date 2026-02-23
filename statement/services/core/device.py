from statement.models import Device
from statement.services.base_service import BaseService


class DeviceService(BaseService):
    """ Serviço para gerenciar dispositivos do usuário. """

    model = Device
    user_field = 'user'
