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
    class_form = SubcategoryForm
    model = Subcategory
    service = SubcategoryService
    redirect_url = 'setup_settings'
