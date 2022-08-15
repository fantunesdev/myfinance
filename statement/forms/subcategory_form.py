from django import forms

from statement.models import Subcategory


class SubcategoryForm(forms.ModelForm):
    class Meta:
        model = Subcategory
        fields = ['description', 'category']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'})
        }
