from django.urls import path

from balanco.views.banco_view import *

urlpatterns = [
    path('cadastrar/', cadastrar_banco, name='cadastrar_banco'),
    path('', listar_bancos, name='listar_bancos'),
    path('editar/<int:id>/', editar_banco, name='editar_banco'),
    path('remover/<int:id>/', remover_banco, name='remover_banco')
]