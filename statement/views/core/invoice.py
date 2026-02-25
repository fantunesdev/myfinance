from statement.services.core.card import CardService
from statement.utils.datetime import DateTimeUtils
from statement.views.core.transaction import TransactionView


class InvoiceView(TransactionView):
    """
    View responsável pela gestão dos lançamentos (invoices) filtrados por card.

    InvoiceView é uma sub-view de TransactionsView e por isso não tem services e templates próprios. Os únicos
    templates customizáveis para essa view são o dashboard e o navigation
    """

    class_title = 'Fatura'

    def __init__(self):
        super().__init__()
        self._card_id = None
        self._instance = None

    def get_current_month(self, request, id):
        year, month = self._get_current_month(request)
        return self.get_by_year_and_month(request, id, year, month)

    def get_by_year_and_month(self, request, id, year, month):
        """
        Sobrescreve a função base passando card_id extraído da URL.
        """
        self._card_id = id
        # Monta os filtros para o mês/ano solicitado
        from django.db.models import Q

        card = CardService.get_by_id(self._card_id)
        # Se o usuário for dependente de algum card_number desse cartão, mostrar
        # apenas os lançamentos do(s) card_number(s) dele, independente do campo
        # `home_screen`. Para o proprietário do cartão, manter o filtro por usuário.
        is_dependent = card.card_numbers.filter(dependente=request.user).exists() and card.user_id != request.user.id

        # date filters: monta usando o usuário e, se for dependente, remove o filtro 'user'
        # para não filtrar por dono da transação (dependentes veem apenas seus card_numbers)
        date_filters = self._set_monthly_filter_by_date_attr('payment', request.user, year, month)
        if is_dependent:
            date_filters.pop('user', None)

        # Include transactions that reference the card directly or via card_number
        instances = self.service.model.objects.filter(
            Q(card=card) | Q(card_number__card=card), **date_filters
        ).select_related('card_number', 'card', 'account')

        # Se for dependente, restringe às transações cujo card_number.dependente seja o usuário
        if is_dependent:
            instances = instances.filter(card_number__dependente=request.user)

        # Monta a estrutura agrupada por CardNumber. Primeiro agrupa transações que
        # referenciam o Card diretamente (card set, card_number null), depois um
        # grupo por CardNumber (caso existam). Isso permite que o template renderize
        # uma seção por número de cartão.
        grouped = []
        # Grupo do cartão pai (transações que referenciam o cartão em si)
        parent_qs = instances.filter(card=card, card_number__isnull=True)
        from django.db.models import Sum

        parent_total = parent_qs.aggregate(total=Sum('value'))['total'] or 0
        # Se o cartão possui CardNumbers cadastrados, prefere mostrar apenas
        # as seções por CardNumber. Inclui o grupo do cartão-pai apenas quando
        # houver transações no nível do cartão (para evitar cabeçalhos vazios).
        if card.card_numbers.exists():
            if parent_qs.exists():
                grouped.append(
                    {'label': card.description, 'card_number': None, 'transactions': parent_qs, 'total': parent_total}
                )
        else:
            grouped.append(
                {'label': card.description, 'card_number': None, 'transactions': parent_qs, 'total': parent_total}
            )

        # Grupos por card_number: inclui grupos mesmo quando vazios para que o
        # template mostre a mensagem "Nenhum lançamento neste cartão.". Se o
        # usuário for dependente, incluir apenas o(s) card_number(s) dele.
        for cn in card.card_numbers.all().order_by('number'):
            if is_dependent and getattr(cn, 'dependente_id', None) != request.user.id:
                continue
            cn_qs = instances.filter(card_number=cn)
            cn_total = cn_qs.aggregate(total=Sum('value'))['total'] or 0
            label = cn.name if getattr(cn, 'name', None) else cn.number
            grouped.append({'label': label, 'card_number': cn, 'transactions': cn_qs, 'total': cn_total})

        template = self._set_template_by_global_status('get_all')
        specific_context = self._set_specific_context(instances, year, month)
        # Adiciona a lista agrupada para renderizar a fatura sem quebrar a lógica do dashboard
        specific_context.update({'grouped_instances': grouped, 'instance': card})
        return self._render(request, None, template, specific_context)

    def _set_additional_filters(self, **kwargs):
        """
        Sobrescreve a classe mãe configurando o filtro adicional de card_id.

        :kwargs (dict): Os filtros para o select.

        :seealso: Consulte os atributos do modelo em statement/models.py
        :seealso: https://docs.djangoproject.com/en/4.2/ref/models/querysets/#filter
        """
        if self._card_id:
            card = CardService.get_by_id(self._card_id)
            self._instance = card
            return {'card': card}
        return {}

    def _set_specific_context(self, instances, year, month):
        return {
            'instances': instances,
            **self._set_dashboard_templatetags(instances, year, month),
            **self.set_navigation_templatetags(year, month),
            'year_month': DateTimeUtils.date(year, month, 1),
            'instance': self._instance,
        }
