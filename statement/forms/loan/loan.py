from django import forms

from statement.forms.base_form import BaseForm
from statement.models import Loan


class LoanForm(BaseForm):
    class Meta:
        model = Loan
        fields = [
            'description',
            'status',
            'notes',
        ]
        widgets = {
            'description': forms.TextInput(),
            'status': forms.Select(),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control textarea',
                    'rows': 6,
                },
            ),
        }
