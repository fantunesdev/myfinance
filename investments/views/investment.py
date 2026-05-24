from django.urls import reverse_lazy

from investments.forms.investment import InvestmentForm
from investments.models import Investment
from investments.services.investment import InvestmentService
from investments.views.base import InvestmentCrudView


class InvestmentView(InvestmentCrudView):
    class_title = 'Investimentos'
    class_form = InvestmentForm
    model = Investment
    service = InvestmentService
    redirect_url = reverse_lazy('get_all_investment')
    column_names = ['Descrição', 'Ativo', 'Broker', 'Status']
    list_fields = ['description', 'asset', 'broker', 'status_label']
