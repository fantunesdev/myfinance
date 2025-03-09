from django.urls import path

from statement.views.core.category import CategoryView

category_view = CategoryView()

urlpatterns = [
    path('cadastrar/', category_view.create, name='create_category'),
    path('editar/<int:id>/', category_view.update, name='update_category'),
    path('remover/<int:id>/', category_view.delete, name='delete_category'),
]
