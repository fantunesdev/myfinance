from statement.forms.core.subcategory import SubcategoryForm
from statement.models import Subcategory
from statement.services.core.subcategory import SubcategoryService
from statement.views.base_view import BaseView


class SubcategoryView(BaseView):
    """
    View responsável pela gestão das subcategorias
    """

    class_has_user = True
    class_title = 'Subcategoria'
    column_names = ['Descrição', 'Categoria']
    class_form = SubcategoryForm
    list_fields = ['description', 'category']
    model = Subcategory
    service = SubcategoryService
    redirect_url = 'setup_settings'
    actions_list = {
        'create': True,
        'delete': True,
        'detail': False,
        'get_all': True,
        'update': True,
    }
    template_is_global = {
        'create': True,
        'delete': True,
        'detail': True,
        'get_all': False,
        'update': True,
    }
