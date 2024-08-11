from django import forms

from statement.models import Flag


class FlagForm(forms.ModelForm):
    class Meta:
        model = Flag
        fields = ['description', 'icon']
        widgets = {'description': forms.TextInput(attrs={'class': 'form-control'})}
