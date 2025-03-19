from statement.services.core.card import CardService
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
        year, month = self._get_current_month()
        return self.get_by_year_and_month(request, id, year, month)

    def get_by_year_and_month(self, request, id, year, month):
        """
        Sobrescreve a função base passando card_id extraído da URL.
        """
        self._card_id = id
        return super().get_by_year_and_month(request, year, month)

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
            'instance': self._instance,
        }
