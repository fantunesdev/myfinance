from django import forms
from django.utils import timezone

from statement.forms.base_form import BaseForm
from statement.forms.widgets import SimpleRichTextWidget
from statement.models import Dream
from statement.utils.notes_html import sanitize_notes


class DreamForm(BaseForm):
    def clean_notes(self):
        return sanitize_notes(self.cleaned_data.get('notes', ''))

    class Meta:
        today = timezone.now()
        model = Dream
        fields = [
            'description',
            'target_value',
            'limit_date',
            'completion_date',
            'status',
            'notes',
        ]
        widgets = {
            'description': forms.TextInput(),
            'target_value': forms.NumberInput(),
            'limit_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'value': today,
                    'class': 'form-control date-input',
                },
            ),
            'completion_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control date-input',
                },
            ),
            'status': forms.Select(),
            'notes': SimpleRichTextWidget(
                attrs={
                    'class': 'form-control textarea',
                    'rows': 6,
                },
            ),
        }
