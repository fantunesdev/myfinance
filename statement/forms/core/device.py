from statement.forms.base_form import BaseForm
from statement.models import Device


class DeviceForm(BaseForm):
    class Meta:
        model = Device
        fields = ['name']
