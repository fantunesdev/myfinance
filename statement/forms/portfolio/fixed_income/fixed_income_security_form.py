from django import forms

from statement.models import FixedIncomeSecurity


class FixedIncomeSecurityForm(forms.ModelForm):
    class Meta:
        model = FixedIncomeSecurity
        fields = ['description', 'abbreviation']

        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'abbreviation': forms.TextInput(attrs={'class': 'form-control'}),
        }
