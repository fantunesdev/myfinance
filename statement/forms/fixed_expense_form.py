from django import forms
from django.utils import timezone

from statement.models import FixedExpenses

today = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')


class FixedExpensesForm(forms.ModelForm):
    class Meta:
        model = FixedExpenses
        fields = ['start_date', 'end_date', 'description', 'value']
        widgets = {
            'start_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'value': today,
                    'class': 'form-control date-input',
                },
            ),
            'end_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control date-input',
                },
            ),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.NumberInput(attrs={'class': 'form-control'}),
        }
