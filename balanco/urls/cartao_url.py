from django.urls import path

from balanco.views.cartao_views import *
from balanco.views.fatura_view import *

urlpatterns = [
    path('cadastrar/', cadastrar_cartao, name='cadastrar_cartao'),
    path('', listar_cartoes, name='listar_cartoes'),
    path('editar/<int:id>/', editar_cartao, name='editar_cartao'),
    path('remover/<int:id>/', remover_cartao, name='remover_cartao'),

    path('<int:cartao_id>/fatura/mes_atual/', listar_fatura_mes_atual, name='listar_fatura_mes_atual'),
    path('<int:cartao_id>/fatura/<int:ano>/<int:mes>/', listar_fatura_ano_mes, name='listar_fatura_ano_mes'),
]
