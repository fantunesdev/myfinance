from django.urls import path

from statement.views.portfolio.fixed_income.index_views import *

urlpatterns = [
    path('cadastrar/', create_index, name='create_index'),
    path('editar/<int:id>/', update_index, name='update_index'),
    path('remover/<int:id>/', delete_index, name='delete_index'),
]
