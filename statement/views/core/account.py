from statement.forms.core.account import AccountForm
from statement.models import Account
from statement.services.core.account import AccountService
from statement.views.base_view import BaseView

class AccountView(BaseView):
    """
    View responsável pela gestão das categorias
    """
    class_has_user = True
    class_title = 'Conta'
    form_class = AccountForm
    model = Account
    service = AccountService
    redirect_url = 'setup_settings'
