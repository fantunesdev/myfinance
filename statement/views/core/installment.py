from statement.forms.core.installment import InstallmentForm
from statement.models import Installment
from statement.services.core.installment import InstallmentService
from statement.services.core.transaction import TransactionService
from statement.views.base_view import BaseView


class InstallmentView(BaseView):
    """
    View responsável pela gestão das contas
    """

    class_has_user = True
    class_title = 'Parcelamento'
    class_form = InstallmentForm
    model = Installment
    service = InstallmentService
    redirect_url = 'get_current_month_transactions'


    def __init__(self):
        """
        Atualiza o dicionário template_is_global sem sobrescrever toda a estrutura da classe base.
        """
        super().__init__()
        self.template_is_global.update(
            {
                'delete': False,
                'detail': False,
                'update': False,
            }
        )
        self._first_transaction = None

    def update(self, request, id):
        kwargs = {
            'installment': id,
            'user': request.user,
        }
        self._first_transaction = TransactionService.get_by_filter(**kwargs).first()
        return super().update(request, id)

    def _add_context_on_templatetags(self, request, instance):
        return {
            'transactions': TransactionService.get_by_filter(installment=instance)
        }

    def _set_form(self, request, instance):
        """
        Sobrescreve a função da classe pai para retornar um formulário customizado
        """
        return InstallmentForm(request.POST or None, instance=self._first_transaction)

    def _custom_actions(self, form, instance):
        """
        Customiza ações
        """
        reorder_dates = form.cleaned_data['']
