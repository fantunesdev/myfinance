from django import forms
from django.forms import TextInput

from balanco.models import Categoria


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['descricao', 'cor', 'icone', 'tipo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descricao': TextInput(attrs={'class': 'form-control'}),
            'cor': TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'icone': TextInput(attrs={'class': 'form-control'})
        }