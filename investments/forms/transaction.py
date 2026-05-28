from investments.forms.base import DateInput, UserFilteredModelForm
from investments.models import InvestmentTransaction


class InvestmentTransactionForm(UserFilteredModelForm):
    user_filtered_fields = ('investment',)

    class Meta:
        model = InvestmentTransaction
        exclude = ['operation_id', 'statement_transaction', 'user']
        labels = {
            'investment': 'Investimento',
            'date': 'Data',
            'type': 'Tipo',
            'amount': 'Valor',
            'quantity': 'Quantidade',
            'unit_price': 'Preço unitário',
            'current_value': 'Valor atual',
            'notes': 'Anotações',
        }
        widgets = {
            'date': DateInput(),
        }
