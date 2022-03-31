from django.urls import path

from balanco.views.cartao_views import *

urlpatterns = [
    path('cadastrar/', cadastrar_cartao, name='cadastrar_cartao'),
    path('', listar_cartoes, name='listar_cartoes'),
    path('editar/<int:id>/', editar_cartao, name='editar_cartao'),
    path('remover/<int:id>/', remover_cartao, name='remover_cartao')
]
