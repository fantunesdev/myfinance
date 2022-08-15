from django import forms


class ExclusionForm(forms.Form):
    confirmation = forms.BooleanField(label='', required=True)
