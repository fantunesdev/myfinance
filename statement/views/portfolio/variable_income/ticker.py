from statement.forms.portfolio.variable_income.ticker import TickerForm
from statement.models import Ticker
from statement.services.portfolio.variable_income.ticker import TickerService
from statement.views.base_view import BaseView

class TickerView(BaseView):
    class_has_user = False
    class_title = 'papel'
    class_form = TickerForm
    model = Ticker
    service = TickerService
    redirect_url = 'setup_settings'
