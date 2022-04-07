from django import forms

from balanco.models import Cartao


class CartaoForm(forms.ModelForm):
    class Meta:
        model = Cartao
        fields = ['bandeira', 'icone', 'descricao', 'limite', 'conta', 'vencimento', 'fechamento', 'tela_inicial']
        widgets = {
            'bandeira': forms.Select(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'limite': forms.NumberInput(attrs={'class': 'form-control'}),
            'conta': forms.Select(attrs={'class': 'form-control'}),
            'vencimento': forms.NumberInput(attrs={'class': 'form-control'}),
            'fechamento': forms.NumberInput(attrs={'class': 'form-control'}),
        }
