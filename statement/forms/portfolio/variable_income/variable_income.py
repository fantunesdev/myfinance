from django import forms
from django.forms import TextInput

from statement.forms.base_form import BaseForm
from statement.models import VariableIncome


class VariableIncomeForm(BaseForm):
    """Formulário para o modelo VariableIncome."""
    class Meta:
        """Metadados do formulário."""
        model = VariableIncome
        fields = ['account', 'ticker']
        widgets = {
            'account': forms.Select(),
            'ticker': forms.Select(),
        }
