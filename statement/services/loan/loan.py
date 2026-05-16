from django.db import models

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
        return cls.model.objects.filter(user=user, status='active')

    @classmethod
    def get_inactive_loans(cls, user):
        """
        Retorna todos os empréstimos inativos de um usuário.
        """
        return cls.model.objects.filter(user=user, status='inactive')

    @classmethod
    def get_balance(cls, loan):
        """
        Retorna o saldo atual de um empréstimo.
        """
        total = loan.entries.aggregate(total=models.Sum('value'))['total']
        return total if total is not None else 0
