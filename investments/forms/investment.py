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
        fields = ['date', 'amount', 'notes']
        labels = {
            'date': 'Data',
            'amount': 'Valor',
            'notes': 'Anotações',
        }
        widgets = {
            'date': DateInput(),
        }


class InvestmentApplicationFromWalletForm(forms.Form):
    investment = forms.ModelChoiceField(label='Investimento de destino', queryset=Investment.objects.none())
    date = forms.DateField(label='Data', input_formats=['%Y-%m-%d'], widget=DateInput())
    amount = forms.DecimalField(
        label='Valor',
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
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
    notes = forms.CharField(
        label='Anotações',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
