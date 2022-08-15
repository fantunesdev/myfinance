from django import forms

from statement.models import Bank


class BankForm(forms.ModelForm):
    class Meta:
        model = Bank
        fields = ['description', 'code', 'icon']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'})
        }
