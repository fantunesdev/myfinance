from django import forms

from .movimentacao_form import MovimentacaoForm


class ParcelamentoForm(MovimentacaoForm):
    data_efetivacao = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    pagas = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
