from investments.forms.base import UserFilteredModelForm
from investments.models import Broker


class BrokerForm(UserFilteredModelForm):
    class Meta:
        model = Broker
        exclude = ['user']
        labels = {
            'description': 'Descrição',
            'kind': 'Tipo',
        }
