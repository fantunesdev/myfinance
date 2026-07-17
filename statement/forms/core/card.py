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
            'prepaid',
        ]
        widgets = {
            'flag': forms.Select(),
            'description': forms.TextInput(),
            'limits': forms.NumberInput(),
            'account': forms.Select(),
            'expiration_day': forms.NumberInput(),
            'closing_day': forms.NumberInput(),
            'prepaid': forms.CheckboxInput(),
        }


class CardNumberForm(forms.ModelForm):
    visible_to = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '6'}),
        label='Dependentes com acesso a este número',
    )

    class Meta:
        model = CardNumber
        fields = ['number', 'name', 'home_screen', 'dependente', 'visible_to']
        widgets = {
            'number': forms.TextInput(attrs={'placeholder': 'Número do cartão'}),
        }

    dependente = forms.ModelChoiceField(
        queryset=User.objects.all(), required=False, widget=forms.Select(), label='Dependente'
    )

    def __init__(self, *args, card=None, **kwargs):
        super().__init__(*args, **kwargs)
        if card is not None:
            self.fields['visible_to'].queryset = User.objects.filter(dependent_card_numbers__card=card).distinct()


# Formset para gerenciar múltiplos números de cartão
CardNumberFormSet = inlineformset_factory(Card, CardNumber, form=CardNumberForm, extra=1, can_delete=True)
