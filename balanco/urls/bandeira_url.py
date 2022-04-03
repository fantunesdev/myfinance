from django.urls import path

from ..views.bandeira_view import *

urlpatterns = [
    path('cadastrar/', cadastrar_bandeira, name='cadastrar_bandeira'),
    path('', listar_bandeiras, name='listar_bandeiras'),
    path('bandeira/<int:id>/', editar_bandeira, name='editar_bandeira'),
    path('remover/<int:id>/', remover_bandeira, name='remover_bandeira')
]
