from statement.forms.base_form import BaseForm
from statement.models import Notification


class NotificationForm(BaseForm):
    """Formulário para o modelo Notification."""

    class Meta:
        """Metadados do formulário."""

        model = Notification
        fields = '__all__'
