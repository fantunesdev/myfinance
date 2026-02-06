from statement.forms.core.notification import NotificationForm
from statement.models import Notification
from statement.services.core.notification import NotificationService
from statement.views.base_view import BaseView


class NotificationView(BaseView):
    """
    View responsável pela gestão das notificações
    """

    class_has_user = False
    class_title = 'Notificação'
    class_form = NotificationForm
    model = Notification
    service = NotificationService
    redirect_url = 'setup_settings'
