from django import forms
from django.utils import timezone

from .transaction_forms import TransactionForm

today = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')


class InstallmentForm(TransactionForm):
    payment_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}
        ),
    )

    paid = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )

    reorder_release_dates = forms.ChoiceField(
        choices=((False, 'Não'), (True, 'Sim')),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )


class AdvanceInstallmentForm(forms.Form):
    quantity = forms.IntegerField(
        label='Quantidade',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    initial_date = forms.DateField(
        label='Data Inicial',
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'value': today,
                'class': 'form-control',
            },
        ),
    )
