from statement.models import CategorizationFeedback
from statement.services.base_service import BaseService


class CategorizationFeedbackService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo CategorizationFeedback."""

    model = CategorizationFeedback
    user_field = 'user'
