from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from statement.models import CategorizationFeedback
from statement.services.core.categorization_feedback import CategorizationFeedbackService
from statement.views.core.categorization_feedback import CategorizationFeedbackView as StatementView


class CategorizationFeedbackView(BaseView):
    """
    Classe que gerencia a view das cartões na API.
    """

    model = CategorizationFeedback
    service = CategorizationFeedbackService
    serializer = BaseSerializer
    statement_view = StatementView
