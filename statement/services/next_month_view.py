from statement.models import NextMonthView
from statement.services.base_service import BaseService


class NextMonthViewService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo NextMonthView."""

    model = NextMonthView
    user_field = 'user'

    @classmethod
    def create(cls, **kwargs):
        cls.model.objects.create(**kwargs)
