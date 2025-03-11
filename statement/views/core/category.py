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
