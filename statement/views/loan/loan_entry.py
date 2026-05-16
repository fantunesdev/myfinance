from django.urls import reverse_lazy

from statement.forms.loan.loan_entry import LoanEntryForm
from statement.models import LoanEntry
from statement.services.loan.loan_entry import LoanEntryService
from statement.views.base_view import BaseView


class LoanEntryView(BaseView):
    """
    View responsável pela gestão dos lançamentos de empréstimos.
    """

    class_has_user = True
    class_title = 'Lançamentos de Empréstimo'
    class_form = LoanEntryForm
    model = LoanEntry
    service = LoanEntryService
    redirect_url = reverse_lazy('get_loans_by_status', args=['ativos'])
    column_names = ['Empréstimo', 'Data', 'Descrição', 'Valor']
    list_fields = ['loan', 'date', 'description', 'value']

    def _set_form(self, request, instance):
        """
        Filtra o campo de empréstimo pelo usuário logado.
        """
        match self._context:
            case 'create':
                if request.method == 'POST':
                    return self.class_form(request.POST, request.FILES or None, user=request.user)
                initial = {}
                if request.GET.get('loan'):
                    initial['loan'] = request.GET.get('loan')
                return self.class_form(initial=initial, user=request.user)
            case 'update':
                return self.class_form(request.POST or None, request.FILES or None, instance=instance, user=request.user)
            case _:
                raise ValueError('Sem contexto definido.')
