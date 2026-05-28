from django.urls import reverse_lazy

from investments.forms.transaction import InvestmentTransactionForm
from investments.models import InvestmentTransaction
from investments.services.transaction import InvestmentTransactionService
from investments.views.base import InvestmentCrudView


class InvestmentTransactionView(InvestmentCrudView):
    class_title = 'Movimentações'
    class_form = InvestmentTransactionForm
    model = InvestmentTransaction
    service = InvestmentTransactionService
    redirect_url = reverse_lazy('investments_dashboard')
    column_names = ['Data', 'Investimento', 'Tipo', 'Valor']
    list_fields = ['date', 'investment', 'type_label', 'amount']
