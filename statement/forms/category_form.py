from django import forms
from django.forms import TextInput

from statement.models import Category


class CategoryForm(forms.ModelForm):
    ignore = forms.BooleanField(required=False)

    class Meta:
        model = Category
        fields = ['type', 'description', 'color', 'icon', 'ignore']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'description': TextInput(attrs={'class': 'form-control'}),
            'color': TextInput(
                attrs={'type': 'color', 'class': 'form-control'}
            ),
            'icon': TextInput(attrs={'class': 'form-control'}),
        }
