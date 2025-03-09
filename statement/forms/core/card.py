from django import forms

from statement.forms.base_form import BaseForm
from statement.models import Card


class CardForm(BaseForm):
    class Meta:
        model = Card
        fields = [
            'flag',
            'icon',
            'description',
            'limits',
            'account',
            'expiration_day',
            'closing_day',
            'home_screen',
            'file_handler_conf',
        ]
        widgets = {
            'flag': forms.Select(),
            'description': forms.TextInput(),
            'limits': forms.NumberInput(),
            'account': forms.Select(),
            'expiration_day': forms.NumberInput(),
            'closing_day': forms.NumberInput(),
            'file_handler_conf': forms.Textarea(attrs={'class': 'form-control textarea'}),
        }
