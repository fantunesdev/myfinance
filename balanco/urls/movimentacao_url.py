from django.urls import path

from balanco.views.movimentacao_view import *

urlpatterns = [
    path('<str:tipo>/cadastrar/', cadastrar_movimentacao, name='cadastrar_movimentacao'),
    path('', listar_movimentacoes, name='listar_movimentacoes'),
    path('ano/<int:ano>/', listar_movimentacoes_ano, name='listar_movimentacoes_ano'),
    path('<int:id>/', detalhar_movimentacao, name='detalhar_movimentacao'),
    path('mes_atual/', listar_mes_atual, name='listar_mes_atual'),
    path('<int:ano>/<int:mes>/', listar_movimentacoes_ano_mes, name='listar_movimentacoes_ano_mes'),
    path('conta/<int:id>/', listar_movimentacoes_conta_id, name='listar_movimentacoes_conta_id'),
    path('editar/<int:id>/', editar_movimentacao, name='editar_movimentacao'),
    path('remover/<int:id>', remover_movimentacao, name='remover_movimentacao')
]
