from investments.forms.base import UserFilteredModelForm
from investments.models import Asset


class AssetForm(UserFilteredModelForm):
    class Meta:
        model = Asset
        exclude = ['user']
        labels = {
            'description': 'Descrição',
            'symbol': 'Código',
            'asset_type': 'Tipo',
            'income_behavior': 'Renda',
            'currency': 'Moeda',
        }
