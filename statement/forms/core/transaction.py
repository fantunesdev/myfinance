from django import forms
from django.utils import timezone

from statement.forms.base_form import BaseForm
from statement.models import Transaction
from statement.services.core.category import CategoryService
from statement.services.core.subcategory import SubcategoryService

today = timezone.localtime(timezone.now()).strftime('%Y-%m-%d')


class TransactionForm(BaseForm):
    """Formulário para o modelo Transaction."""

    type = forms.ChoiceField(
        label='Tipo',
        choices=(('entrada', 'Entrada'), ('saida', 'Saída')),
        required=False,
        widget=forms.Select(),
    )

    payment_method = forms.ChoiceField(
        required=False,
        widget=forms.Select(),
        choices=(
            (1, 'Cartão de Crédito'),
            (2, 'Conta Corrente'),
        ),
    )

    home_screen = forms.BooleanField(required=False)

    class Meta:
        """Metadados do formulário."""

        model = Transaction
        fields = '__all__'
        exclude = ['user']
        widgets = {
            'release_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'value': today}),
            'payment_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'value': today}),
            'observation': forms.Textarea(attrs={'class': 'form-control textarea'}),
        }


class TransactionTypeForm(TransactionForm):
    """Classe base para filtrar categorias por tipo."""

    transaction_type = None

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields.pop('type', None)

        if self.transaction_type:
            self.fields['category'].queryset = CategoryService.get_by_type(self.transaction_type)
        self.fields['subcategory'].queryset = SubcategoryService.get_all()


class TransactionExpenseForm(TransactionTypeForm):
    """Formulário para despesas"""

    transaction_type = 'saida'


class TransactionRevenueForm(TransactionTypeForm):
    """Formulário para entradas"""

    transaction_type = 'entrada'


class UpdateTransactionForm(TransactionForm):
    """Formulário de update"""

    INSTALLMENT_CHOICES = (
        ('editar', 'Editar este registro sem alterar o número de parcelas'),
        ('parcelar', 'Adicionar ou remover parcelas'),
    )
    installment_option = forms.ChoiceField(
        choices=INSTALLMENT_CHOICES,
        widget=forms.Select(),
    )
