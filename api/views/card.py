from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from statement.models import Card
from statement.services.core.card import CardService
from statement.views.core.card import CardView as StatementView


class CardView(BaseView):
    """
    Classe que gerencia a view das cartões na API.
    """

    model = Card
    service = CardService
    serializer = BaseSerializer
    statement_view = StatementView
