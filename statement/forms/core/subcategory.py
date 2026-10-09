from statement.forms.base_form import BaseForm
from statement.models import Subcategory


SUBCATEGORY_HELP_TEXTS = {
    'is_investment': (
        'Marca esta subcategoria como investimento. No demonstrativo anual, quando a exibição estiver ativa, '
        'os lançamentos aparecem na fatia Investimentos em vez de Despesas.'
    ),
}


class SubcategoryForm(BaseForm):
    """Formulário para o modelo Subcategory."""

    class Meta:
        """Metadados do formulário."""

        model = Subcategory
        fields = '__all__'
        labels = {
            'is_investment': 'Investimento',
        }
        help_texts = SUBCATEGORY_HELP_TEXTS
