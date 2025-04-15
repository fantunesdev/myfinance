from statement.forms.base_form import BaseForm
from statement.models import CategorizationFeedback


class CategorizationFeedbackForm(BaseForm):
    """Formulário para o modelo CategorizationFeedback."""

    class Meta:
        """Metadados do formulário."""

        model = CategorizationFeedback
        fields = '__all__'
