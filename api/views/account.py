from api.views.base_view import BaseView
from api.serializers.base_serializer import BaseSerializer
from statement.models import Account
from statement.services.core.account import AccountService
from statement.views.core.account import AccountView as StatementView


class AccountView(BaseView):
    """
    Classe que gerencia a view das contas na API.
    """

    model = Account
    service = AccountService
    serializer = BaseSerializer
    statement_view = StatementView
