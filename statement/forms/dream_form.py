from django import forms
from django.utils import timezone

from statement.models import Dream

today = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')


class DreamForm(forms.ModelForm):
    class Meta:
        model = Dream
        fields = [
            'description',
            'value',
            'limit_date',
        ]
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.NumberInput(attrs={'class': 'form-control'}),
            'limit_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'value': today,
                    'class': 'form-control date-input',
                },
            ),
        }
