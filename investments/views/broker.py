from django.urls import reverse_lazy

from investments.forms.broker import BrokerForm
from investments.models import Broker
from investments.services.broker import BrokerService
from investments.views.base import InvestmentCrudView


class BrokerView(InvestmentCrudView):
    class_title = 'Brokers'
    class_form = BrokerForm
    model = Broker
    service = BrokerService
    redirect_url = reverse_lazy('get_all_broker')
    column_names = ['Descrição', 'Tipo']
    list_fields = ['description', 'kind_label']
