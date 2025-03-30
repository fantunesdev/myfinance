from api.serializers.subcategory import SubcategorySerializer
from api.views.base_view import BaseView
from statement.services.core.subcategory import SubcategoryService
from statement.views.core.subcategory import SubcategoryView as StatementView


class SubcategoryView(BaseView):
    """
    Classe que gerencia a view das subcategorias na API.
    """

    service = SubcategoryService
    serializer = SubcategorySerializer
    statement_view = StatementView
