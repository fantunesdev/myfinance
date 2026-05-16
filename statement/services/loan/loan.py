from django.db import models
from django.db.models import Value
from django.db.models.functions import Coalesce

from statement.models import Loan
from statement.services.base_service import BaseService


class LoanService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Loan."""

    model = Loan
    user_field = 'user'

    @classmethod
    def get_active_loans(cls, user):
        """
        Retorna todos os empréstimos ativos de um usuário.
        """
        return cls._with_balance(cls.model.objects.filter(user=user, status='active'))

    @classmethod
    def get_inactive_loans(cls, user):
        """
        Retorna todos os empréstimos inativos de um usuário.
        """
        return cls._with_balance(cls.model.objects.filter(user=user, status='inactive'))

    @classmethod
    def _with_balance(cls, queryset):
        """
        Adiciona o saldo atual ao queryset para uso na listagem.
        """
        return queryset.annotate(
            balance=Coalesce(models.Sum('entries__value'), Value(0.0), output_field=models.FloatField())
        )

    @classmethod
    def get_balance(cls, loan):
        """
        Retorna o saldo atual de um empréstimo.
        """
        total = loan.entries.aggregate(total=models.Sum('value'))['total']
        return total if total is not None else 0
