from django import forms
from django.utils import timezone

from balanco.models import Movimentacao, Categoria

attrs = {
    'class': 'form-control'
}
hoje = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')


class MovimentacaoForm(forms.ModelForm):
    tipo = forms.ChoiceField(
        label="Tipo",
        choices=(
            ('entrada', 'Entrada'),
            ('saida', 'Saída')
        ),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    meio_de_pagamento = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        choices=(
            (1, 'Cartão de Crédito'),
            (2, 'Conta Corrente'),
        )
    )

    tela_inicial = forms.BooleanField(
        required=False
    )

    class Meta:
        model = Movimentacao

        fields = [
            'tela_inicial', 'data_lancamento', 'data_efetivacao', 'conta', 'cartao', 'categoria', 'subcategoria',
            'descricao', 'valor', 'numero_parcelas', 'pagas', 'fixa', 'anual', 'moeda', 'observacao', 'tipo', 'lembrar',
            'efetivado'
        ]

        widgets = {
            'data_lancamento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'value': hoje, 'class': 'form-control'}
            ),
            'data_efetivacao': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control', 'value': hoje}
            ),
            'valor': forms.NumberInput(attrs={'class': 'form-control'}),
            'numero_parcelas': forms.NumberInput(attrs={'class': 'form-control'}),
            'pagas': forms.NumberInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'subcategoria': forms.Select(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'conta': forms.Select(attrs={'class': 'form-control'}),
            'cartao': forms.Select(attrs={'class': 'form-control'}),
            'moeda': forms.Select(attrs={'class': 'form-control'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control textarea'})
        }


class MovimentacaoSaidaForm(MovimentacaoForm):
    categoria = forms.ModelChoiceField(queryset=Categoria.objects.filter(tipo='saida'),
                                       widget=forms.Select(attrs={'class': 'form-control'}))


class MovimentacaoEntradaForm(MovimentacaoForm):
    categoria = forms.ModelChoiceField(queryset=Categoria.objects.filter(tipo='entrada'),
                                       widget=forms.Select(attrs={'class': 'form-control'}))


class EditarFormMovimentacao(MovimentacaoForm):
    PARCELAR_CHOICES = (
        ('editar', 'Editar este registro sem alterar o número de parcelas'),
        ('parcelar', 'Adicionar ou remover parcelas')
    )
    parcelar = forms.ChoiceField(
        choices=PARCELAR_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
