from django import forms
from django.forms import TextInput

from statement.forms.base_form import BaseForm
from statement.models import Category


class CategoryForm(BaseForm):
    """Formulário para o modelo Category."""

    class Meta:
        """Metadados do formulário."""

        model = Category
        fields = ['type', 'description', 'color', 'icon']
        widgets = {
            'type': forms.Select(),
            'description': TextInput(),
            'color': TextInput(attrs={'type': 'color'}),
            'icon': TextInput(),
        }
