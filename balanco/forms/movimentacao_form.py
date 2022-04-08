from django import forms
from django.utils import timezone

from balanco.models import Movimentacao, Categoria

attrs = {
    'class': 'form-control'
}
hoje = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')
fields = ['data_lancamento', 'data_efetivacao', 'conta', 'cartao', 'categoria', 'subcategoria', 'descricao', 'valor',
          'numero_parcelas', 'pagas', 'fixa', 'anual', 'moeda', 'observacao', 'lembrar', 'efetivado', 'tela_inicial']
widgets = {
    'data_lancamento': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date',
                                                                 'value': hoje,
                                                                 'class': 'form-control'}),
    'data_efetivacao': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date',
                                                                 'class': 'form-control',
                                                                 'value': hoje}),
    'valor': forms.NumberInput(attrs={'class': 'form-control'}),
    'numero_parcelas': forms.NumberInput(attrs={'class': 'form-control'}),
    'pagas': forms.NumberInput(attrs={'class': 'form-control'}),
    'subcategoria': forms.Select(attrs={'class': 'form-control'}),
    'descricao': forms.TextInput(attrs={'class': 'form-control'}),
    'conta': forms.Select(attrs={'class': 'form-control'}),
    'cartao': forms.Select(attrs={'class': 'form-control'}),
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
