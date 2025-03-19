from django import forms
from django.utils import timezone

from statement.models import Account, FixedIncome

today = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')


class FixedIncomeForm(forms.ModelForm):
    """
    Formulário para criação e de investimentos de renda fixa.

    Inclui os campos do modelo FixedIncome e adiciona o campo extra days
    """

    days = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control date-input'}))

    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(type_id=3), required=True, widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        """
        Metadados para o formulário FixedIncomeForm.

        Define o modelo e os campos a serem incluídos no formulário.
        """

        model = FixedIncome
        fields = [
            'account',
            'security',
            'principal',
            'investment_date',
            'maturity_date',
            'index',
            'contractual_rate',
            'days',
        ]

        widgets = {
            'account': forms.Select(attrs={'class': 'form-control'}),
            'security': forms.Select(attrs={'class': 'form-control'}),
            'principal': forms.NumberInput(attrs={'class': 'form-control'}),
            'investment_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'value': today,
                    'class': 'form-control date-input',
                },
            ),
            'maturity_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control date-input',
                },
            ),
            'index': forms.Select(attrs={'class': 'form-control'}),
            'contractual_rate': forms.NumberInput(attrs={'class': 'form-control'}),
        }
