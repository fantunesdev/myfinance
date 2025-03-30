from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from statement.models import Bank
from statement.services.core.bank import BankService
from statement.views.core.bank import BankView as StatementView


class BankView(BaseView):
    """
    Classe que gerencia a view das contas na API.
    """

    model = Bank
    service = BankService
    serializer = BaseSerializer
    statement_view = StatementView
