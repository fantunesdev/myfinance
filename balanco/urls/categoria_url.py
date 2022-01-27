from django.urls import path
from ..views.categoria_view import *

urlpatterns = [
    path('cadastrar/', cadastrar_categoria, name='cadastrar_categoria'),
    path('', listar_categorias, name='listar_categorias'),
    path('<str:tipo>/', listar_categorias_tipo, name='listar_categorias_tipo'),
    path('editar/<int:id>/', editar_categoria, name='editar_categoria'),
    path('remover/<int:id>/', remover_categoria, name='remover_categoria'),
]