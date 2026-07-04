from django import forms

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
        fields = ['date', 'due_date', 'amount', 'quantity', 'unit_price', 'notes']
        labels = {
            'date': 'Data',
            'due_date': 'Vencimento',
            'amount': 'Valor',
            'quantity': 'Quantidade',
            'unit_price': 'Preço unitário',
            'notes': 'Anotações',
        }
        widgets = {
            'date': DateInput(),
            'due_date': DateInput(),
        }

    def __init__(self, *args, investment=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not self._show_quantity_fields(investment):
            self.fields.pop('quantity', None)
            self.fields.pop('unit_price', None)

    @staticmethod
    def _show_quantity_fields(investment):
        if not investment:
            return False
        return investment.asset.asset_type in ['variable_income', 'crypto', 'currency']


class InvestmentApplicationFromWalletForm(forms.Form):
    investment = forms.ModelChoiceField(label='Investimento de destino', queryset=Investment.objects.none())
    date = forms.DateField(label='Data', input_formats=['%Y-%m-%d'], widget=DateInput())
    due_date = forms.DateField(label='Vencimento', input_formats=['%Y-%m-%d'], required=False, widget=DateInput())
    amount = forms.DecimalField(
        label='Valor',
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
    )
    quantity = forms.DecimalField(
        label='Quantidade',
        max_digits=20,
        decimal_places=8,
        min_value=0.00000001,
        required=False,
    )
    unit_price = forms.DecimalField(
        label='Preço unitário',
        max_digits=14,
        decimal_places=6,
        min_value=0.000001,
        required=False,
    )
    notes = forms.CharField(
        label='Anotações',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, user=None, wallet=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            queryset = Investment.objects.filter(user=user)
            if wallet:
                queryset = queryset.exclude(id=wallet.id)
            self.fields['investment'].queryset = queryset

        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class InvestmentRedemptionForm(forms.Form):
    date = forms.DateField(label='Data', input_formats=['%Y-%m-%d'], widget=DateInput())
    principal_amount = forms.DecimalField(
        label='Principal resgatado',
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
    )
    amount = forms.DecimalField(
        label='Valor recebido no caixa',
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
    )
    quantity = forms.DecimalField(
        label='Quantidade',
        max_digits=20,
        decimal_places=8,
        min_value=0.00000001,
        required=False,
    )
    unit_price = forms.DecimalField(
        label='Preço unitário',
        max_digits=14,
        decimal_places=6,
        min_value=0.000001,
        required=False,
    )
    notes = forms.CharField(
        label='Anotações',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, investment=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not InvestmentCashMovementForm._show_quantity_fields(investment):
            self.fields.pop('quantity', None)
            self.fields.pop('unit_price', None)

        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
