from django import forms


class ExclusaoForm(forms.Form):
    confirmacao = forms.BooleanField(label='', required=True)


class MeioPagamentoForm(forms.Form):
    CHOICES = [
        (1, 'Cartão de Crédito'),
        (2, 'Conta Corrente'),
    ]

    meio_de_pagamento = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        choices=CHOICES
    )

