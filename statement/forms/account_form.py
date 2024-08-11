from django import forms

from statement.models import Account


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            'bank',
            'branch',
            'number',
            'balance',
            'limits',
            'type',
            'home_screen',
            'file_handler_conf',
        ]
        widgets = {
            'bank': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control'}),
            'limits': forms.NumberInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'file_handler_conf': forms.Textarea(attrs={'class': 'form-control textarea'}),
        }
