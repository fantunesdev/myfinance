from statement.forms.base_form import BaseForm
from statement.models import Flag


class FlagForm(BaseForm):
    """Formulário para o modelo Flag."""
    class Meta:
        """Metadados do formulário."""
        model = Flag
        fields = '__all__'
