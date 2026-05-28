from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.decorators import method_decorator

from investments.services.investment import InvestmentService
from investments.services.transaction import InvestmentTransactionService
from statement.views.base_view import BaseView


class InvestmentsDashboardView(BaseView):
    class_title = 'Investimentos'

    @method_decorator(login_required)
    def dashboard(self, request):
        context = InvestmentService.get_dashboard(request.user)
        context['default_wallet'] = InvestmentTransactionService.get_default_wallet(request.user)
        return self._render(request, None, 'investments/dashboard.html', context)

    @method_decorator(login_required)
    def create_default_wallet(self, request):
        if request.method == 'POST':
            InvestmentTransactionService.get_or_create_default_wallet(request.user)
            messages.success(request, 'Carteira padrão criada com sucesso.')
        return redirect('investments_dashboard')
