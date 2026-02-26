from datetime import date, datetime

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
        # Tratamento especial para 'user' para incluir transações visíveis aos dependentes
        user = kwargs.pop('user', None)

        if user is not None:
            # Extrai filtro home_screen se presente e delega à função protegida
            home_screen_filter = kwargs.pop('home_screen') if 'home_screen' in kwargs else None
            return cls._visible_transactions_for_user(
                user=user, filters=kwargs, home_screen=home_screen_filter, order=order, first=first
            )

        if first:
            return Transaction.objects.filter(**kwargs).first()
        transactions = Transaction.objects.filter(**kwargs)
        if order:
            return transactions.order_by(order)
        return transactions

    @classmethod
    def _visible_transactions_for_user(cls, user, filters=None, home_screen=None, order=None, first=False):
        """
        Retorna um queryset com as transações visíveis ao `user`.

        - Para o dono (`user` igual ao campo `user`): aplica todos os filtros fornecidos,
          incluindo `home_screen` quando informado.
        - Para dependentes (quando `card_number.dependente == user`): aplica os mesmos
          filtros, EXCETO `home_screen` — dependentes veem suas transações mesmo que
          `home_screen` seja False.

        :param user: usuário para o qual calcular visibilidade
        :param filters: dicionário de filtros adicionais (ex.: datas, card, account)
        :param home_screen: valor explícito de home_screen (ou None)
        :param order: campo de ordenação (opcional)
        :param first: se True retorna apenas a primeira instância
        """
        filters = dict(filters or {})

        owner_filters = dict(filters)
        if home_screen is not None:
            owner_filters['home_screen'] = home_screen

        owner_qs = Transaction.objects.filter(user=user, **owner_filters)

        dependent_filters = dict(filters)
        dependent_qs = Transaction.objects.filter(card_number__dependente=user, **dependent_filters)

        qs = (owner_qs | dependent_qs).distinct()
        if first:
            return qs.first()
        if order:
            return qs.order_by(order)
        return qs

    @classmethod
    def get_last_twelve_months_by_year_and_month(cls, year, month, user):
        """
        Obtém os lançamentos dos últimos doze meses a partir de um mês e um ano especificados
        """
        end_date = datetime(year, month, 1)
        start_date = end_date - relativedelta(months=11)
        # Reutiliza get_by_filter para garantir mesmo comportamento de visibilidade
        return cls.get_by_filter(
            payment_date__gte=start_date, payment_date__lte=end_date, user=user, home_screen=True
        ).order_by('posted_date')

    @staticmethod
    def _set_home_screen(instance):
        """
        Seta o atributo home_screen.

        Ou Transaction tem uma instância de account, ou tem uma instância de card. Se a instância
        account for setada, seta home_screeen de acordo com o que está definido na conta ou no cartão.

        :instance: Uma instância do model Transaction
        """
        # Preferir a configuração específica do número do cartão quando presente
        if getattr(instance, 'card_number', None):
            return instance.card_number.home_screen
        if getattr(instance, 'card', None):
            return instance.card.home_screen
        if getattr(instance, 'account', None):
            return instance.account.home_screen
        # Retornar ao valor da instância (ou ao padrão do modelo) como fallback
        return instance.home_screen
