from django.contrib.auth.decorators import user_passes_test
from django.urls import path

from statement.views.core.subcategory import SubcategoryView

subcategory_view = SubcategoryView()

staff_required = user_passes_test(lambda u: u.is_staff)

urlpatterns = [
    path('', staff_required(subcategory_view.get_all), name='get_all_subcategory'),
    path('cadastrar/', staff_required(subcategory_view.create), name='create_subcategory'),
    path('editar/<int:id>/', staff_required(subcategory_view.update), name='update_subcategory'),
    path('remover/<int:id>/', staff_required(subcategory_view.delete), name='delete_subcategory'),
]
