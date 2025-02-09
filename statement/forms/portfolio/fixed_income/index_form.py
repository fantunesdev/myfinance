from django import forms

from statement.models import Index


class IndexForm(forms.ModelForm):
    class Meta:
        model = Index
        fields = ['description', 'bcb_id', 'first_date']

        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'bcb_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'first_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control date-input',
                },
            ),
        }
