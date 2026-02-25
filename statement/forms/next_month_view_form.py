from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from statement.services.next_month_view import NextMonthViewService


class NextMonthViewForm(forms.Form):
    day = forms.IntegerField(
        label='Dia',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )

    active = forms.BooleanField(label='Antecipar visualização do mês?', required=False)

    def save(self, user):
        data = self.cleaned_data
        return NextMonthViewService.create(user=user, day=data.get('day'), active=data.get('active', False))
