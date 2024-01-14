from django.urls import path

from statement.views.flag_views import *

urlpatterns = [
    path('cadastrar/', create_flag, name='create_flag'),
    path('editar/<int:id>/', update_flag, name='update_flag'),
    path('remover/<int:id>/', delete_flag, name='delete_flag'),
]
