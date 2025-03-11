from django.utils import timezone

from statement.services.base_service import BaseService
from statement.models import Dream


class DreamService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Dream."""
    model = Dream
    user_field = 'user'
    today = timezone.now()

    @classmethod
    def get_active_dreams(cls, user):
        """
        Retorna todos os sonhos ativos de um usuário (data maior ou igual à data atual).
        """
        return Dream.objects.filter(user=user, limit_date__gte=cls.today)

    @classmethod
    def get_past_dreams(cls, user):
        """
        Retorna todos os sonhos que já foram alcançados o que não estão mais ativos.
        """
        return Dream.objects.filter(user=user, limit_date__lt=cls.today)
