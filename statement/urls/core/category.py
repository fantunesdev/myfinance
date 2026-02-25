from django.contrib.auth.decorators import user_passes_test
from django.urls import path

from statement.views.core.category import CategoryView

category_view = CategoryView()

staff_required = user_passes_test(lambda u: u.is_staff)

urlpatterns = [
    path('cadastrar/', staff_required(category_view.create), name='create_category'),
    path('editar/<int:id>/', staff_required(category_view.update), name='update_category'),
    path('remover/<int:id>/', staff_required(category_view.delete), name='delete_category'),
]
