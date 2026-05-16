from django import forms

from statement.forms.base_form import BaseForm
from statement.models import Loan, LoanEntry
from statement.utils.datetime import DateTimeUtils

today = DateTimeUtils.today()


class LoanEntryForm(BaseForm):
    def __init__(self, *args, user=None, **kwargs):
        """
        Filtra os empréstimos disponíveis pelo usuário logado.
        """
        super().__init__(*args, **kwargs)
        if user:
            self.fields['loan'].queryset = Loan.objects.filter(user=user)

    class Meta:
        model = LoanEntry
        fields = [
            'loan',
            'date',
            'description',
            'value',
        ]
        widgets = {
            'date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'value': today,
                    'class': 'date-input',
                },
            ),
            'description': forms.TextInput(),
            'value': forms.NumberInput(),
        }
