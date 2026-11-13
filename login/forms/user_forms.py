from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from login.models import Profile, User


class InactivityLogoutForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['inactivity_logout_enabled', 'inactivity_logout_minutes']
        labels = {
            'inactivity_logout_enabled': 'Sair automaticamente por inatividade',
            'inactivity_logout_minutes': 'Tempo de inatividade em minutos',
        }
        help_texts = {
            'inactivity_logout_enabled': 'A atividade em qualquer aba do MyFinance mantém o acesso neste navegador.',
            'inactivity_logout_minutes': 'Informe de 1 a 1440 minutos. Atualizações automáticas não renovam o prazo.',
        }
        widgets = {
            'inactivity_logout_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 1440}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['inactivity_logout_minutes'].required = False

    def clean_inactivity_logout_minutes(self):
        minutes = self.cleaned_data.get('inactivity_logout_minutes')
        if minutes is None and self.cleaned_data.get('inactivity_logout_enabled'):
            raise forms.ValidationError('Informe o tempo de inatividade em minutos.')
        return minutes if minutes is not None else (self.instance.inactivity_logout_minutes or 10)


class UserForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='Confirmação senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        attrs = {'class': 'form-control'}
        model = User
        fields = ['name', 'email', 'username', 'photo']
        widgets = {
            'name': forms.TextInput(attrs=attrs),
            'email': forms.TextInput(attrs=attrs),
            'username': forms.TextInput(attrs=attrs),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 != password2:
            raise forms.ValidationError('As senhas informadas não são iguais')
        return password2

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get('password2')
        if password:
            try:
                validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error('password2', error)


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
