from django import forms
from django.utils import timezone

from statement.models import FixedIncome

today = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')

class FixedIncomeForm(forms.ModelForm):
    class Meta:
        model = FixedIncome
        fields = ['account', 'security', 'principal', 'investment_date', 'maturity_date', 'index', 'contractual_rate']

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