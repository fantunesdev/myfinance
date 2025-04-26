from statement.models import CategorizationFeedback
from statement.services.base_service import BaseService


class CategorizationFeedbackService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo CategorizationFeedback."""

    model = CategorizationFeedback
    user_field = 'user'

    @classmethod
    def set_as_trained(cls, instance):
        """
        Marca o feedback como já utilizado para treino.

        :param: instance - Uma instância do modelo CategorizationFeedback
        """
        instance.is_used_for_training = True
        instance.save()
        return instance

    @classmethod
    def get_untrained(cls):
        """
        Obtém as os feedbacks que ainda não foram usados para treino
        """
        return cls.model.objects.filter(is_used_for_training=False)
