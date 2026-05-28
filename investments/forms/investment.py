from investments.forms.base import DateInput, UserFilteredModelForm
from investments.models import Investment
from investments.models import InvestmentTransaction


class InvestmentForm(UserFilteredModelForm):
    user_filtered_fields = ('asset', 'broker')

    class Meta:
        model = Investment
        exclude = ['user']
        labels = {
            'description': 'Descrição',
            'asset': 'Ativo',
            'broker': 'Broker',
            'start_date': 'Data inicial',
            'due_date': 'Vencimento',
            'status': 'Status',
            'notes': 'Anotações',
        }
        widgets = {
            'start_date': DateInput(),
            'due_date': DateInput(),
        }


class InvestmentCashMovementForm(UserFilteredModelForm):
    class Meta:
        model = InvestmentTransaction
        fields = ['date', 'amount', 'notes']
        labels = {
            'date': 'Data',
            'amount': 'Valor',
            'notes': 'Anotações',
        }
        widgets = {
            'date': DateInput(),
        }
