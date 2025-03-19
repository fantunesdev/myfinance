from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from statement.forms.general_forms import NavigationForm
from statement.utils.datetime import DateTimeUtils
from statement.views.base_view import BaseView


class DashboardView(BaseView):
    """
    View responsável pelo html base dos dashboards
    """

    @method_decorator(login_required)
    def show_dashboard(self, request):
        """
        Renderiza um html base para os dashboards
        """
        today = DateTimeUtils.today()
        form = NavigationForm(initial={'year': today.year, 'month': today.month})
        return self._render(request, form, 'dashboards/index.html')
