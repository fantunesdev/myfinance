from django import forms

from ..models import Conta


class ContaForm(forms.ModelForm):
    class Meta:
        model = Conta
        fields = ['banco', 'agencia', 'numero', 'saldo', 'limite', 'tipo', 'tela_inicial']
        widgets = {
            'banco': forms.Select(attrs={'class': 'form-control'}),
            'agencia': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'saldo': forms.NumberInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'limite': forms.NumberInput(attrs={'class': 'form-control'}),
        }
