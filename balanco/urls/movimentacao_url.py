from django.urls import path

from balanco.views.movimentacao_view import *

urlpatterns = [
    path('<str:tipo>/cadastrar/', cadastrar_movimentacao, name='cadastrar_movimentacao'),
    path('', listar_movimentacoes, name='listar_movimentacoes'),
    path('editar/<int:id>/', editar_movimentacao, name='editar_movimentacao'),
    path('remover/<int:id>', remover_movimentacao, name='remover_movimentacao')
]
