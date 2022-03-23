from django.urls import path

from balanco.views.conta_view import *

urlpatterns = [
    path('cadastrar/', cadastrar_conta, name='cadastrar_conta'),
    path('', listar_contas, name='listar_contas'),
    path('editar/<int:id>/', editar_conta, name='editar_conta'),
    path('remover/<int:id>/', remover_conta, name='remover_conta')
]