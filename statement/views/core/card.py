from statement.forms.core.card import CardForm
from statement.models import Card
from statement.services.core.card import CardService
from statement.views.base_view import BaseView

class CardView(BaseView):
    """
    View responsável pela gestão das categorias
    """
    class_has_user = True
    class_title = 'Cartão'
    class_form = CardForm
    model = Card
    service = CardService
    redirect_url = 'setup_settings'
