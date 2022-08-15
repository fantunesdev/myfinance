from django.urls import path

from statement.views.category_views import *

urlpatterns = [
    path('cadastrar/', create_category, name='create_category'),
    path('editar/<int:id>/', update_category, name='update_category'),
    path('remover/<int:id>/', delete_category, name='delete_category'),
]
