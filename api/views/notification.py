from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from statement.models import Notification
from statement.services.core.notification import NotificationService
from statement.views.core.notification import NotificationView as StatementView


class NotificationView(BaseView):
    """
    Classe que gerencia a view das contas na API.
    """

    model = Notification
    service = NotificationService
    serializer = BaseSerializer
    statement_view = StatementView
