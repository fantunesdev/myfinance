from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from statement.models import Subcategory
from statement.services.core.subcategory import SubcategoryService
from statement.views.core.subcategory import SubcategoryView as StatementView


class SubcategoryView(BaseView):
    """
    Classe que gerencia a view das subcategorias na API.
    """

    model = Subcategory
    service = SubcategoryService
    serializer = BaseSerializer
    statement_view = StatementView
