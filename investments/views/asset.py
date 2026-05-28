from django.urls import reverse_lazy

from investments.forms.asset import AssetForm
from investments.models import Asset
from investments.services.asset import AssetService
from investments.views.base import InvestmentCrudView


class AssetView(InvestmentCrudView):
    class_title = 'Ativos'
    class_form = AssetForm
    model = Asset
    service = AssetService
    redirect_url = reverse_lazy('investments_dashboard')
    column_names = ['Descrição', 'Código', 'Tipo', 'Moeda']
    list_fields = ['description', 'symbol', 'asset_type_label', 'currency']
