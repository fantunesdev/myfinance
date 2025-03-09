from statement.forms.core.subcategory import SubcategoryForm
from statement.models import Subcategory
from statement.services.core.subcategory import SubcategoryService
from statement.views.base_view import BaseView

class SubcategoryView(BaseView):
    """
    View responsável pela gestão das categorias
    """
    class_has_user = True
    class_title = 'Subcategoria'
    form_class = SubcategoryForm
    model = Subcategory
    service = SubcategoryService
    redirect_url = 'setup_settings'
