from django.urls import path

from balanco.views.conta_view import *

urlpatterns = [
    path('cadastrar/', cadastrar_conta, name='cadastrar_conta'),
    path('', listar_contas, name='listar_contas'),
    path('editar/<int:id>/', editar_conta, name='editar_conta'),
    path('remover/<int:id>/', remover_conta, name='remover_conta'),

    path('<int:conta_id>/', listar_movimentacoes_conta, name='listar_movimentacoes_conta'),
    path('<int:conta_id>/mes_atual/', listar_conta_mes_atual, name='listar_conta_mes_atual'),
    path('<int:conta_id>/<int:ano>/', listar_movimentacoes_conta_ano, name='listar_movimentacoes_conta_ano'),
    path('<int:conta_id>/<int:ano>/<int:mes>/', listar_movimentacoes_conta_ano_mes, name='listar_movimentacoes_conta_ano_mes'),
]
