from django import forms
from django.forms import inlineformset_factory

from login.models import User
from statement.forms.base_form import BaseForm
from statement.models import Card, CardNumber


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
        ]
        widgets = {
            'flag': forms.Select(),
            'description': forms.TextInput(),
            'limits': forms.NumberInput(),
            'account': forms.Select(),
            'expiration_day': forms.NumberInput(),
            'closing_day': forms.NumberInput(),
        }


class CardNumberForm(forms.ModelForm):
    class Meta:
        model = CardNumber
        fields = ['number', 'name', 'home_screen', 'dependente']
        widgets = {
            'number': forms.TextInput(attrs={'placeholder': 'Número do cartão'}),
        }

    dependente = forms.ModelChoiceField(
        queryset=User.objects.all(), required=False, widget=forms.Select(), label='Dependente'
    )


# Formset para gerenciar múltiplos números de cartão
CardNumberFormSet = inlineformset_factory(Card, CardNumber, form=CardNumberForm, extra=1, can_delete=True)
