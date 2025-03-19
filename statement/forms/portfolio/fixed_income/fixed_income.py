from django import forms

from statement.utils.datetime import DateTimeUtils
from statement.forms.base_form import BaseForm
from statement.models import FixedIncome


today = DateTimeUtils.today()

class FixedIncomeForm(BaseForm):
    """Formulário para o modelo FixedIncome."""

    class Meta:
        """Metadados do formulário."""

        model = FixedIncome
        fields = '__all__'
        exclude = ['user']
        widgets = {
            'investment_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'value': today,
                    'class': 'date-input',
                },
            ),
            'maturity_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'date-input',
                },
            ),
        }
