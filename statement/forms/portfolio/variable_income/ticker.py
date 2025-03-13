from statement.forms.base_form import BaseForm
from statement.models import Ticker


class TickerForm(BaseForm):
    """Formulário para o modelo Ticker."""

    class Meta:
        """Metadados do formulário."""

        model = Ticker
        fields = '__all__'
