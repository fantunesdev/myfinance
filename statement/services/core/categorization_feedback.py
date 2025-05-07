from statement.models import CategorizationFeedback
from statement.services.base_service import BaseService


class CategorizationFeedbackService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo CategorizationFeedback."""

    model = CategorizationFeedback
    user_field = 'user'

    @classmethod
    def set_subcategory_training_status(cls, instance):
        """
        Marca o feedback como já utilizado para treino.

        :param: instance - Uma instância do modelo CategorizationFeedback
        """
        instance.subcategory_training = True
        instance.save()
        return instance

    @classmethod
    def get_subcategory_untrained(cls, user):
        """
        Obtém as os feedbacks que ainda não foram usados para treino
        """
        return cls.model.objects.filter(user=user, subcategory_training=False)

    @classmethod
    def set_description_training_status(cls, instance):
        """
        Marca o feedback como já utilizado para treino.

        :param: instance - Uma instância do modelo CategorizationFeedback
        """
        instance.description_training = True
        instance.save()
        return instance

    @classmethod
    def get_description_untrained(cls, user):
        """
        Obtém as os feedbacks que ainda não foram usados para treino de descrição
        """
        return cls.model.objects.filter(user=user, description_training=False)

    @classmethod
    def reset_feedback(cls, user):
        """
        Marca todos os feedbacks como não treinados
        """
        feedbacks = cls.get_all(user)

        for feedback in feedbacks:
            feedback.category_training = False
            feedback.description_training = False
            feedback.save()

    @classmethod
    def reset_subcategory_feedback(cls, user):
        """
        Marca todos os feedbacks como não treinados
        """
        print('passou aqui')
        feedbacks = cls.get_all(user)

        for feedback in feedbacks:
            feedback.subcategory_training = False
            feedback.save()

    @classmethod
    def reset_description_feedback(cls, user):
        """
        Marca todos os feedbacks como não treinados
        """
        feedbacks = cls.get_all(user)

        for feedback in feedbacks:
            feedback.description_training = False
            feedback.save()

    @classmethod
    def delete_feedbacks(cls, user):
        """
        Apaga os feedbacks cadastrados do usuário.
        """
        feedbacks = cls.get_all(user)

        for feedback in feedbacks:
            feedback.delete()
