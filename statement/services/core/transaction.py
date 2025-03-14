from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.db.models import Q

from statement.models import Transaction
from statement.services.base_service import BaseService


class TransactionService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Transaction."""

    model = Transaction
    user_field = 'user'

    @classmethod
    def create(cls, form, user=None, id=None):
        """
        Sobrescreve o método 'create' da classe mãe redefinindo o atributo home_screen
        """
        instance = form.save(commit=False)
        instance.home_screen = cls._set_home_screen(instance)
        return super().create(form, user=user)

    @classmethod
    def update(cls, form, instance):
        """
        Sobrescreve o método 'update' da classe mãe redefinindo o atributo home_screen
        """
        instance = form.save(commit=False)
        instance.home_screen = cls._set_home_screen(instance)
        return super().update(form, instance)

    @classmethod
    def get_by_filter(cls, order=None, **kwargs):
        """
        Obtém os lançamentos de acordo com filtros passados em um dicionário. Podendo ordenar por
        algum campo selecionado.
        """
        transactions = Transaction.objects.filter(**kwargs)
        if order:
            return transactions.order_by(order)
        return transactions

    @classmethod
    def get_last_twelve_months_by_year_and_month(cls, year, month, user):
        """
        Obtém os lançamentos dos últimos doze meses a partir de um mês e um ano especificados
        """
        end_date = datetime(year, month, 1)
        start_date = end_date - relativedelta(months=11)
        return Transaction.objects.filter(
            Q(payment_date__gte=start_date) & Q(payment_date__lte=end_date),
            user=user,
            home_screen=True,
        ).order_by('release_date')

    @staticmethod
    def _set_home_screen(instance):
        """
        Seta o atributo home_screen.

        Ou Transaction tem uma instância de account, ou tem uma instância de card. Se a instância
        account for setada, seta home_screeen de acordo com o que está definido na
        """
        if instance.account:
            return instance.account.home_screen
        return instance.card.home_screen
