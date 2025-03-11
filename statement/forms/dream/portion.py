from django import forms
from django.utils import timezone

from statement.models import Portion

today = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')


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
