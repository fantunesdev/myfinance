from django import forms


class ExclusaoForm(forms.Form):
    confirmacao = forms.BooleanField(label='', required=True)
