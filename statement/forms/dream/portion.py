from django import forms

from statement.models import Portion
from statement.utils.datetime import DateTimeUtils


today = DateTimeUtils.today()

class PortionForm(forms.ModelForm):
    class Meta:
        model = Portion
        fields = [
            'date',
            'value',
        ]
        widgets = {
            'date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'value': today,
                    'class': 'form-control date-input',
                },
            ),
            'value': forms.NumberInput(attrs={'class': 'form-control'}),
        }
