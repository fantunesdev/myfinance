from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator

from statement.forms.loan.loan import LoanForm
from statement.models import Loan
from statement.services.loan.loan import LoanService
from statement.views.base_view import BaseView


class LoanView(BaseView):
    """
    View responsável pela gestão de empréstimos.
    """

    class_has_user = True
    class_title = 'Empréstimos'
    class_form = LoanForm
    model = Loan
    service = LoanService
    redirect_url = reverse_lazy('get_loans_by_status', args=['ativos'])
    column_names = ['Descrição', 'Saldo']
    list_fields = ['description', 'balance']

    def __init__(self):
        super().__init__()
        self.template_is_global.update(
            {
                'detail': False,
            }
        )

    @method_decorator(login_required)
    def get_by_status(self, request, status):
        """
        Obtém empréstimos de acordo com o status.
        """
        if status == 'ativos':
            loans = self.service.get_active_loans(request.user)
        elif status == 'inativos':
            loans = self.service.get_inactive_loans(request.user)
        else:
            raise Http404('Status inválido')
        actions_list = self.actions_list.copy()
        if status == 'inativos':
            actions_list.update(
                {
                    'create': False,
                    'delete': False,
                    'update': False,
                }
            )
        specific_content = {
            'instances': loans,
            'fields': self.list_fields,
            'loan_status': status,
            'actions_list': actions_list,
            'show_duplicate_checker': False,
        }
        return self._render(request, None, 'loan/list.html', specific_content)

    def _add_context_on_templatetags(self, request, instance):
        """
        Retorna os lançamentos relacionados ao empréstimo.
        """
        return {
            'entries': instance.entries.filter(user=request.user).order_by('-date'),
            'balance': self.service.get_balance(instance),
        }
