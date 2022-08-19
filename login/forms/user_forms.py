from django import forms
from django.contrib.auth.forms import AuthenticationForm

from login.models import User


class UserForm(forms.ModelForm):
    password1 = forms.CharField(label='Senha', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label='Confirmação senha', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        attrs = {'class': 'form-control'}
        model = User
        fields = ['name', 'email', 'username', 'photo']
        widgets = {
            'name': forms.TextInput(attrs=attrs),
            'email': forms.TextInput(attrs=attrs),
            'username': forms.TextInput(attrs=attrs)
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 != password2:
            raise forms.ValidationError('As senhas informadas não são iguais')
        return password2


class LoginForm(AuthenticationForm):
    attrs = {'class': 'form-control'}
    username = forms.CharField(widget=forms.TextInput(attrs=attrs))
    password = forms.CharField(widget=forms.PasswordInput(attrs=attrs))

    class Meta:
        model = User
        fields = ['username', 'password']


class ProfileForm(forms.ModelForm):
    attrs = {'class': 'form-control'}

    name = forms.CharField(widget=forms.TextInput(attrs=attrs))
    email = forms.CharField(widget=forms.EmailInput(attrs=attrs))
    username = forms.CharField(widget=forms.TextInput(attrs=attrs))

    class Meta:
        model = User
        fields = ['name', 'email', 'username', 'photo']
