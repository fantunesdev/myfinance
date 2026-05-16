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
            'target_value',
            'limit_date',
            'completion_date',
            'status',
            'notes',
        ]
        widgets = {
            'description': forms.TextInput(),
            'target_value': forms.NumberInput(),
            'limit_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'value': today,
                    'class': 'form-control date-input',
                },
            ),
            'completion_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control date-input',
                },
            ),
            'status': forms.Select(),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control textarea',
                    'rows': 6,
                },
            ),
        }
