from django import forms
from django.utils import timezone

from .movimentacao_form import MovimentacaoForm

hoje = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')


class ParcelamentoForm(MovimentacaoForm):
    data_efetivacao = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    pagas = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    reordenar_datas_lancamento = forms.ChoiceField(
        choices=(
            (False, 'Não'),
            (True, 'Sim')
        ),
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class AdiantarParcelaForm(forms.Form):
    quantidade = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}))
    data_inicial = forms.DateField(
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'value': hoje,
                'class': 'form-control',
            }
        )
    )
