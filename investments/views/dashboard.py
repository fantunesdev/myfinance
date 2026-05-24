from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from investments.services.investment import InvestmentService
from statement.views.base_view import BaseView


class InvestmentsDashboardView(BaseView):
    class_title = 'Investimentos'

    @method_decorator(login_required)
    def dashboard(self, request):
        context = InvestmentService.get_dashboard(request.user)
        return self._render(request, None, 'investments/dashboard.html', context)
