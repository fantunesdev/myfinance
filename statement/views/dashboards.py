from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from statement.forms.general_forms import NavigationForm
from statement.utils.datetime import DateTimeUtils
from statement.views.base_view import BaseView
from statement.services.fuel_entries import fuel_history, summarize_fuel
from statement.services.fuel_tracking import FuelTrackingService


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
        report = summarize_fuel(fuel_history(request.user))
        config = FuelTrackingService.get(request.user)
        if config and config.active and config.subcategory:
            report['category_ids'] = [config.subcategory.category_id]
            report['subcategory_ids'] = [config.subcategory.pk]
        return self._render(request, form, 'dashboards/index.html', {'fuel_report': report})
