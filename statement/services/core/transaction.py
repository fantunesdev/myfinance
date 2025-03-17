from datetime import datetime, date

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
    def get_by_filter(cls, order=None, first=False, **kwargs):
        """
        Obtém os lançamentos de acordo com filtros passados em um dicionário. Podendo ordenar por
        algum campo selecionado.
        """
        if first:
            return Transaction.objects.filter(**kwargs).first()
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
        account for setada, seta home_screeen de acordo com o que está definido na conta ou no cartão.

        :instance: Uma instância do model Transaction
        """
        if instance.account:
            return instance.account.home_screen
        return instance.card.home_screen

    @staticmethod
    def set_card_release_date(transaction):
        """
        Seta uma data de vencimento para uma transação de acordo com o fechamento e o vencimento do cartão

        :transaction: Uma instância do model Transaction
        """
        if transaction.card:
            payment_date = date(
                transaction.release_date.year,
                transaction.release_date.month,
                transaction.card.expiration_day,
            )
            if transaction.release_date.day >= transaction.card.closing_day:
                payment_date += relativedelta(months=2)
            return payment_date
        else:
            message = f'Nenhum cartão setado para o lançamento {transaction.description} com o id {transaction.id}.'
            raise ValueError(message)
