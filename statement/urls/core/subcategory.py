from django.urls import path

from statement.views.core.subcategory import SubcategoryView

subcategory_view = SubcategoryView()

urlpatterns = [
    path('cadastrar/', subcategory_view.create, name='create_subcategory'),
    path('editar/<int:id>/', subcategory_view.update, name='update_subcategory'),
    path('remover/<int:id>/', subcategory_view.delete, name='delete_subcategory'),
]
