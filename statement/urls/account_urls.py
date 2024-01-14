from django.urls import include, path

from statement.views.account_views import *

urlpatterns = [
    path('cadastrar/', create_account, name='create_account'),
    path('editar/<int:id>/', update_account, name='update_account'),
    path('remover/<int:id>/', delete_account, name='delete_account'),
]
