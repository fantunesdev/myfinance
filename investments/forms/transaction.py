from investments.forms.base import DateInput, UserFilteredModelForm
from investments.models import InvestmentTransaction


class InvestmentTransactionForm(UserFilteredModelForm):
    user_filtered_fields = ('investment',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.user:
            self.instance.user = self.user

    class Meta:
        model = InvestmentTransaction
        exclude = ['operation_id', 'statement_transaction', 'user', 'affects_value']
        labels = {
            'investment': 'Investimento',
            'date': 'Data',
            'due_date': 'Vencimento',
            'type': 'Tipo',
            'amount': 'Valor',
            'quantity': 'Quantidade',
            'unit_price': 'Preço unitário',
            'current_value': 'Valor atual',
            'notes': 'Anotações',
        }
        widgets = {
            'date': DateInput(),
            'due_date': DateInput(),
        }
