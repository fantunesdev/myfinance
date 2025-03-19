from django import forms

from statement.forms.base_form import BaseForm
from statement.models import FixedExpenses
from statement.utils.datetime import DateTimeUtils


today = DateTimeUtils.today()

class FixedExpensesForm(BaseForm):
    class Meta:
        model = FixedExpenses
        fields = '__all__'
        exclude = ['user']
        widgets = {
            'start_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'value': today,
                    'class': 'date-input',
                },
            ),
            'end_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'date-input',
                },
            ),
        }
