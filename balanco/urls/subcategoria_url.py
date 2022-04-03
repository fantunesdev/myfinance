from django.urls import path

from balanco.views.subcategoria_view import *

urlpatterns = [
    path('cadastrar/', cadastrar_subcategoria, name='cadastrar_subcategoria'),
    path('', listar_subcategorias, name='listar_subcategorias'),
    path('editar/<int:id>/', editar_subcategoria, name='editar_subcategoria'),
    path('remover/<int:id>/', remover_subcategoria, name='remover_subcategoria')
]
