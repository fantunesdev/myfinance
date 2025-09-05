from statement.services.core.account import AccountService
from statement.views.core.transaction import TransactionView
from statement.utils.datetime import DateTimeUtils


class ExtractView(TransactionView):
    """
    View responsável pela gestão dos lançamentos (extract) filtrados por account.

    ExtractView é uma sub-view de TransactionsView e por isso não tem services e templates próprios. Os únicos
    templates customizáveis para essa view são o dashboard e o navigation
    """

    class_title = 'Extrato'

    def __init__(self):
        super().__init__()
        self._account_id = None
        self._instance = None

    def get_current_month(self, request, id):
        year, month = self._get_current_month()
        return self.get_by_year_and_month(request, id, year, month)

    def get_by_year_and_month(self, request, id, year, month):
        """
        Sobrescreve a função base passando account_id extraído da URL.
        """
        self._account_id = id
        return super().get_by_year_and_month(request, year, month)

    def _set_additional_filters(self, **kwargs):
        """
        Sobrescreve a classe mãe configurando o filtro adicional de account_id.

        :kwargs (dict): Os filtros para o select.

        :seealso: Consulte os atributos do modelo em statement/models.py
        :seealso: https://docs.djangoproject.com/en/4.2/ref/models/querysets/#filter
        """
        if self._account_id is not None:
            account = AccountService.get_by_id(self._account_id)
            self._instance = account
            return {'account': account}
        return {}

    def _set_specific_context(self, instances, year, month):
        return {
            'instances': instances,
            **self._set_dashboard_templatetags(instances, year, month),
            **self.set_navigation_templatetags(year, month),
            'year_month': DateTimeUtils.date(year, month, 1),
            'instance': self._instance,
        }
