from statement.forms.base_form import BaseForm
from statement.models import Subcategory


class SubcategoryForm(BaseForm):
    """Formulário para o modelo Subcategory."""
    class Meta:
        """Metadados do formulário."""
        model = Subcategory
        fields = '__all__'
