from django import forms

from statement.forms.base_form import BaseForm
from statement.models import Account


class AccountForm(BaseForm):
    class Meta:
        model = Account
        fields = '__all__'
        exclude = ['user']
        widgets = {
            'bank': forms.Select(),
            'branch': forms.TextInput(),
            'number': forms.TextInput(),
            'balance': forms.NumberInput(),
            'limits': forms.NumberInput(),
            'type': forms.Select(),
            'file_handler_conf': forms.Textarea(attrs={'class': 'form-control textarea'}),
        }
