from django import forms

from statement.forms.base_form import BaseForm


class UserFilteredModelForm(BaseForm):
    user_filtered_fields = ()

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            for field_name in self.user_filtered_fields:
                if field_name in self.fields:
                    self.fields[field_name].queryset = self.fields[field_name].queryset.filter(user=user)


class DateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%d')
        super().__init__(*args, **kwargs)
