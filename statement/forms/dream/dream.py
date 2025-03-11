from django import forms
from django.utils import timezone

from statement.forms.base_form import BaseForm
from statement.models import Dream


class DreamForm(BaseForm):
    class Meta:
        today = timezone.now()
        model = Dream
        fields = [
            'description',
            'value',
            'limit_date',
        ]
        widgets = {
            'description': forms.TextInput(),
            'value': forms.NumberInput(),
            'limit_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'value': today,
                    'class': 'form-control date-input',
                },
            ),
        }
