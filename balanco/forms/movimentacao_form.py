from django import forms
from django.utils import timezone

from balanco.models import Movimentacao, Categoria

hoje = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')
fields = ['valor', 'data', 'repetir', 'parcelas', 'descricao', 'categoria', 'conta', 'fixa', 'moeda',
          'observacao', 'lembrar', 'tipo', 'efetivado']
widgets = {
    'valor': forms.NumberInput(attrs={'class': 'form-control'}),
    'data': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date',
                                                      'value': hoje,
                                                      'class': 'form-control'}),
    'parcelas': forms.NumberInput(attrs={'class': 'form-control'}),
    'descricao': forms.TextInput(attrs={'class': 'form-control'}),
    'conta': forms.Select(attrs={'class': 'form-control'}),
    'moeda': forms.Select(attrs={'class': 'form-control'}),
    'observacao': forms.NumberInput(attrs={'class': 'form-control'})
}


class MovimentacaoSaidaForm(forms.ModelForm):
    categoria = forms.ModelChoiceField(queryset=Categoria.objects.filter(tipo='saida'),
                                       widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Movimentacao
        fields = fields
        widgets = widgets


class MovimentacaoEntradaForm(forms.ModelForm):
    categoria = forms.ModelChoiceField(queryset=Categoria.objects.filter(tipo='entrada'),
                                       widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Movimentacao
        fields = fields
        widgets = widgets
