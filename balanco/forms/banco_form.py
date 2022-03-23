from django import forms

from ..models import Banco


class BancoForm(forms.ModelForm):
    class Meta:
        model = Banco
        fields = ['descricao', 'codigo', 'icone']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'})
        }
