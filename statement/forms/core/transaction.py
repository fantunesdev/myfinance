from django import forms

from statement.forms.base_form import BaseForm
from statement.models import CardNumber, Dream, Transaction
from statement.services.core.category import CategoryService
from statement.services.core.subcategory import SubcategoryService
from statement.services.dream.dream import DreamService
from statement.utils.datetime import DateTimeUtils
from statement.access import restrict_write_relations

today = DateTimeUtils.today()


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
    
    dream = forms.ModelChoiceField(
        queryset=Dream.objects.none(),
        required=False,
        widget=forms.Select(),
        label='Sonho/Objetivo'
    )

    class Meta:
        """Metadados do formulário."""

        model = Transaction
        fields = '__all__'
        exclude = ['user']
        widgets = {
            'posted_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'value': today}),
            'payment_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'value': today}),
            'observation': forms.Textarea(attrs={'class': 'form-control textarea'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar sonhos ativos do usuário
        self.fields['dream'].queryset = DreamService.get_active_dreams(user)

        transaction_type = getattr(self, 'transaction_type', None) or self['type'].value()
        self.fields['category'].queryset = CategoryService.get_by_type(transaction_type)
        try:
            category_id = int(self['category'].value())
        except (TypeError, ValueError):
            category_id = None
        self.fields['subcategory'].queryset = SubcategoryService.get_by_category(category_id).filter(
            category__type=transaction_type
        )

        restrict_write_relations(self, user)
        if self.data:
            card_id = self.data.get('card') or self.initial.get('card')
            self.fields['card_number'].queryset = self.fields['card_number'].queryset.filter(card_id=card_id)

    def clean(self):
        cleaned = super().clean()
        number = cleaned.get('card_number')
        card = cleaned.get('card')
        if number and (not card or number.card_id != card.pk):
            self.add_error('card_number', 'O número deve pertencer ao cartão selecionado.')
        return cleaned


class TransactionTypeForm(TransactionForm):
    """Classe base para filtrar categorias por tipo."""

    transaction_type = None

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

        self.fields.pop('type', None)


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
