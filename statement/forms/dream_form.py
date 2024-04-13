from django import forms

from statement.models import Dream


class DreamForm(forms.ModelForm):
    class Meta:
        model = Dream
        fields = [
            'description',
            'value',
            'installments',
        ]
        widgets = {
            'description': forms.TextInput(attrs = {'class': 'form-control'}),
            'value': forms.NumberInput(attrs = {'class': 'form-control'}),
            'installments': forms.NumberInput(attrs = {'class': 'form-control'}),
        }