from django import forms

from statement.models import Card


class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ['flag', 'icon', 'description', 'limits', 'account', 'expiration_day', 'closing_day', 'home_screen', 'file_handler_conf']
        widgets = {
            'flag': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'limits': forms.NumberInput(attrs={'class': 'form-control'}),
            'account': forms.Select(attrs={'class': 'form-control'}),
            'expiration_day': forms.NumberInput(attrs={'class': 'form-control'}),
            'closing_day': forms.NumberInput(attrs={'class': 'form-control'}),

            'file_handler_conf': forms.Textarea(attrs={'class': 'form-control textarea'}),
        }
