from django.contrib.auth.forms import UserChangeForm
from ..models import Usuario
from django import forms


class PerfilForm(UserChangeForm):
    nome = forms.CharField(label='nome', widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.CharField(label='email', widget=forms.EmailInput(attrs={'class': 'form-control'}))
    username = forms.CharField(label='username', widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Usuario
        fields = ['nome', 'email', 'username', 'foto']
