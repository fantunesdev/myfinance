from statement.forms.base_form import BaseForm
from statement.models import Sector


class SectorForm(BaseForm):
    """Formulário para o modelo Sector."""
    class Meta:
        """Metadados do formulário."""
        model = Sector
        fields = '__all__'
