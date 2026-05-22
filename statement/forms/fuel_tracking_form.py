from django import forms

from statement.models import Subcategory
from statement.services.fuel_tracking import FuelTrackingService


class FuelTrackingForm(forms.Form):
    active = forms.BooleanField(label='Acompanhar consumo de combustível?', required=False)
    subcategory = forms.ModelChoiceField(
        label='Subcategoria de combustível',
        queryset=Subcategory.objects.select_related('category').all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('active') and not cleaned_data.get('subcategory'):
            self.add_error('subcategory', 'Informe a subcategoria de combustível.')
        return cleaned_data

    def save(self, user):
        data = self.cleaned_data
        return FuelTrackingService.create(
            user=user,
            active=data.get('active', False),
            subcategory=data.get('subcategory'),
        )
