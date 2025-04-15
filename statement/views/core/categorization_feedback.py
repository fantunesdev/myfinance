from statement.forms.core.categorization_feedback import CategorizationFeedbackForm
from statement.models import CategorizationFeedback
from statement.services.core.categorization_feedback import CategorizationFeedbackService
from statement.views.base_view import BaseView


class CategorizationFeedbackView(BaseView):
    """
    View responsável pela gestão dos cartões
    """

    class_has_user = True
    class_title = 'Feedback de Classificação'
    class_form = CategorizationFeedbackForm
    model = CategorizationFeedback
    service = CategorizationFeedbackService
    redirect_url = 'setup_settings'
