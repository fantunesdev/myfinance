from django import forms

from statement.models import NextMonthView


class NextMonthViewForm(forms.ModelForm):
    day = forms.IntegerField(
        label='Dia', widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    active = forms.BooleanField(
        label='Antecipar visualização do mês?', required=False
    )

    class Meta:
        model = NextMonthView
        fields = ['day', 'active']
