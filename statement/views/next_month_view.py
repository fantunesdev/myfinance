from statement.forms.next_month_view_form import NextMonthViewForm
from statement.models import NextMonthView
from statement.services.next_month_view import NextMonthViewService
from statement.views.base_view import BaseView


class NextMonthViewView(BaseView):
    """
    View responsável pela gestão da visualização do próximo mês
    """

    class_has_user = True
    class_title = 'Conta'
    class_form = NextMonthViewForm
    model = NextMonthView
    service = NextMonthViewService
    redirect_url = 'setup_settings'
