from django.urls import path
from django.contrib.auth.decorators import user_passes_test

from statement.views.core.subcategory import SubcategoryView

subcategory_view = SubcategoryView()

staff_required = user_passes_test(lambda u: u.is_staff)

urlpatterns = [
    path('cadastrar/', staff_required(subcategory_view.create), name='create_subcategory'),
    path('editar/<int:id>/', staff_required(subcategory_view.update), name='update_subcategory'),
    path('remover/<int:id>/', staff_required(subcategory_view.delete), name='delete_subcategory'),
]
