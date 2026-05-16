from statement.models import Loan, LoanEntry
from statement.services.base_service import BaseService


class LoanEntryService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo LoanEntry."""

    model = LoanEntry
    user_field = 'user'

    @classmethod
    def create(cls, form, user=None, id=None):
        instance = form.save(commit=False)
        if id:
            instance.loan = Loan.objects.get(id=id, user=user)
        instance = cls.verify_user_field(instance, user)
        instance.save()
        return instance

    @classmethod
    def get_by_loan(cls, loan_id, user):
        """
        Retorna os lançamentos de um empréstimo do usuário.
        """
        return cls.model.objects.filter(loan_id=loan_id, user=user)
