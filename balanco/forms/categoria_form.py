from django import forms
from django.forms import TextInput

from ..models.movimentacao_model import Categoria


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['descricao', 'cor', 'icone', 'tipo']
        widgets = {
            'descricao': TextInput(attrs={'class': 'form-control'}),
            'cor': TextInput(attrs={'type': 'color'})
        }