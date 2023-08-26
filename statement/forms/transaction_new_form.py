
from django import forms
from django.utils import timezone

from statement.models import Transaction

today = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')


class TransactionNewForm(forms.ModelForm):
    type = forms.ChoiceField(
        label="Tipo",
        choices=(
            ('entrada', 'Entrada'),
            ('saida', 'Saída')
        ),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    payment_method = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        choices=(
            (1, 'Cartão de Crédito'),
            (2, 'Conta Corrente'),
        )
    )

    home_screen = forms.BooleanField(
        required=False
    )

    class Meta:
        model = Transaction

        fields = [
            'release_date', 'payment_date', 'account', 'card', 'category', 'subcategory', 'description', 'value',
            'installments_number', 'paid', 'fixed', 'annual', 'currency', 'observation', 'remember', 'type',
            'effected', 'home_screen'
        ]

        widgets = {
            'release_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'value': today, 'class': 'form-control'}
            ),
            'payment_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control', 'value': today}
            ),
            'account': forms.Select(attrs={'class': 'form-control'}),
            'card': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'subcategory': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.NumberInput(attrs={'class': 'form-control'}),
            'installments_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'paid': forms.NumberInput(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'observation': forms.Textarea(attrs={'class': 'form-control textarea'})
        }
         