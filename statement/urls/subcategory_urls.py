from django.urls import path

from statement.views.subcategory_views import *

urlpatterns = [
    path('cadastrar/', create_subcategory, name='create_subcategory'),
    path('editar/<int:id>/', update_subcategory, name='update_subcategory'),
    path('remover/<int:id>/', delete_subcategory, name='delete_subcategory'),
]
