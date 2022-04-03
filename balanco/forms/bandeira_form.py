from django import forms

from balanco.models import Bandeira


class BandeiraForm(forms.ModelForm):
    class Meta:
        model = Bandeira
        fields = ['descricao', 'icone']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'})
        }
