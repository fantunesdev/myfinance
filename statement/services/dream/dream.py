from django.utils import timezone

from statement.models import Dream
from statement.services.base_service import BaseService


class DreamService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Dream."""

    model = Dream
    user_field = 'user'
    today = timezone.now()

    @classmethod
    def get_active_dreams(cls, user):
        """
        Retorna todos os sonhos com status 'active' de um usuário.
        """
        return Dream.objects.filter(user=user, status='active')

    @classmethod
    def get_past_dreams(cls, user):
        """
        Retorna todos os sonhos que não estão com status 'active'.
        """
        return Dream.objects.filter(user=user).exclude(status='active')

    @classmethod
    def get_paused_dreams(cls, user):
        """
        Retorna todos os sonhos pausados de um usuário.
        """
        return Dream.objects.filter(user=user, status='paused')

    @classmethod
    def get_completed_dreams(cls, user):
        """
        Retorna todos os sonhos concluídos de um usuário.
        """
        return Dream.objects.filter(user=user, status='completed').order_by('-completion_date', 'description')

    @classmethod
    def get_cancelled_dreams(cls, user):
        """
        Retorna todos os sonhos cancelados de um usuário.
        """
        return Dream.objects.filter(user=user, status='cancelled')
