from statement.forms.base_form import BaseForm
from statement.models import Bank


class BankForm(BaseForm):
    """Formulário para o modelo Bank."""
    class Meta:
        """Metadados do formulário."""
        model = Bank
        fields = '__all__'
