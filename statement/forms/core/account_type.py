from statement.forms.base_form import BaseForm
from statement.models import AccountType


class AccountTypeForm(BaseForm):
    """Formulário para o modelo AccountType."""
    class Meta:
        """Metadados do formulário."""
        model = AccountType
        fields = '__all__'
