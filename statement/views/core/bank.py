from statement.forms.core.bank import BankForm
from statement.models import Bank
from statement.services.core.bank import BankService
from statement.views.base_view import BaseView

class BankView(BaseView):
    """
    View responsável pela gestão dos bancos
    """
    class_has_user = True
    class_title = 'Banco'
    class_form = BankForm
    model = Bank
    service = BankService
    redirect_url = 'setup_settings'
