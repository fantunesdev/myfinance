from django import forms

from statement.utils.datetime import DateTimeUtils
from statement.forms.base_form import BaseForm
from statement.models import Index


class IndexForm(BaseForm):
    """Formulário para o modelo Index."""

    class Meta:
        """Metadados do formulário."""

        model = Index
        fields = '__all__'
        exclude = ['user']
        widgets = {
            'first_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control date-input',
                },
            ),
        }
