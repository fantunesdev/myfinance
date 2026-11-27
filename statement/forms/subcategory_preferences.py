from django import forms

from statement.models import Subcategory


class SubcategoryPreferencesForm(forms.Form):
    hidden_subcategories = forms.ModelMultipleChoiceField(
        queryset=Subcategory.objects.all(),
        required=False,
        label='Subcategorias que não uso',
    )
