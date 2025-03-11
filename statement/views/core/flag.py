from statement.forms.core.flag import FlagForm
from statement.models import Flag
from statement.services.core.flag import FlagService
from statement.views.base_view import BaseView

class FlagView(BaseView):
    """
    View responsável pela gestão das categorias
    """
    class_has_user = True
    class_title = 'Bandeira'
    class_form = FlagForm
    model = Flag
    service = FlagService
    redirect_url = 'setup_settings'
