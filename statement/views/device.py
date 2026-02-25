from statement.forms.core.device import DeviceForm
from statement.models import Device
from statement.services.core.device import DeviceService
from statement.views.base_view import BaseView


class DeviceView(BaseView):
    """CRUD de dispositivos no perfil do usuário."""

    class_has_user = True
    class_title = 'Device'
    class_form = DeviceForm
    model = Device
    service = DeviceService
    redirect_url = 'get_profile'

    def _add_context_on_templatetags(self, request, instance):
        # expose devices to the template area in profile
        if self._context in ['get_all', 'detail', 'create', 'update']:
            devices = self.service.get_all(request.user)
            return {'devices': devices}
        return {}


# Wrapper functions to be used in URL patterns (profile area)
def create_device(request, id=None):
    view = DeviceView()
    return view.create(request, id=id)


def get_all_device(request):
    view = DeviceView()
    return view.get_all(request)


def detail_device(request, id):
    view = DeviceView()
    return view.detail(request, id=id)


def update_device(request, id):
    view = DeviceView()
    return view.update(request, id=id)


def delete_device(request, id):
    view = DeviceView()
    return view.delete(request, id=id)
