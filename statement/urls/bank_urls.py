from django.urls import path

from statement.views.bank_views import *

urlpatterns = [
    path('cadastrar/', create_bank, name='create_bank'),
    path('', get_banks, name='get_banks'),
    path('editar/<int:id>/', update_bank, name='update_bank'),
    path('remover/<int:id>/', delete_bank, name='delete_bank')
]