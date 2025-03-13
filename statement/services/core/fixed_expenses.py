import calendar
from datetime import datetime

from django.db.models import Q

from statement.services.base_service import BaseService
from statement.models import FixedExpenses


class FixedExpensesService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo FixedExpenses."""
    model = FixedExpenses
    user_field = 'user'

    @classmethod
    def get_by_filter(cls, **kwargs):
        """
        Retorna as despesas fixas filtradas 
        """
        return cls.model.objects.filter(**kwargs)

    @classmethod
    def get_active_by_date(cls, year, month, user):
        """
        Retorna as despesas fixas por uma data
        """
        first_month_day = datetime(year, month, 1)
        last_month_day = datetime(year, month, calendar.monthrange(year, month)[1])

        return cls.model.objects.filter(
            Q(end_date__gte=last_month_day) | Q(end_date__isnull=True),
            start_date__lte=first_month_day,
            user=user,
        )
