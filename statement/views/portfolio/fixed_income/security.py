from statement.forms.portfolio.fixed_income.security import FixedIncomeSecurityForm
from statement.models import FixedIncomeSecurity
from statement.services.portfolio.fixed_income.security import FixedIncomeSecurityService
from statement.views.base_view import BaseView


class FixedIncomeSecurityView(BaseView):
    class_has_user = False
    class_title = 'papel'
    class_form = FixedIncomeSecurityForm
    model = FixedIncomeSecurity
    service = FixedIncomeSecurityService
    redirect_url = 'setup_settings'
