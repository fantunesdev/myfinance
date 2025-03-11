from statement.forms.core.account_type import AccountTypeForm
from statement.models import AccountType
from statement.services.core.account_type import AccountTypeService
from statement.views.base_view import BaseView

class AccountTypeView(BaseView):
    """
    View responsável pela gestão das categorias
    """
    class_has_user = True
    class_title = 'Tipo de Conta'
    class_form = AccountTypeForm
    model = AccountType
    service = AccountTypeService
    redirect_url = 'setup_settings'
