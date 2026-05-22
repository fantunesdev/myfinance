from statement.forms.core.category import CategoryForm
from statement.models import Category
from statement.services.core.category import CategoryService
from statement.views.base_view import BaseView


class CategoryView(BaseView):
    """
    View responsável pela gestão das categorias
    """

    class_has_user = False
    class_title = 'Categoria'
    class_form = CategoryForm
    model = Category
    service = CategoryService
    redirect_url = 'setup_settings'
    template_is_global = {
        'create': True,
        'delete': True,
        'detail': False,
        'get_all': True,
        'update': True,
    }

    def _add_context_on_templatetags(self, request, instance):
        if self._context != 'detail':
            return {}

        return {
            'subcategories': instance.subcategories.all(),
        }
