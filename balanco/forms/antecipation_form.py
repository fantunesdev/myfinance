from django import forms

from balanco.models import Antecipation


class AntecipationForm(forms.ModelForm):
    day = forms.IntegerField(
        label='Dia',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    active = forms.BooleanField(
        label='Antecipar visualização',
        required=False
    )

    class Meta:
        model = Antecipation
        fields = ['day', 'active']
