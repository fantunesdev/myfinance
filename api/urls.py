from django.urls import path

from api.views.antecipation_views import *
from api.views.cartao_views import *
from api.views.categoria_views import *
from api.views.movimentacao_view import *
from api.views.subcategoria_views import *

urlpatterns = [
    path('antecipation/', AntecipationList.as_view(), name='antecipation-list'),
    path('cartoes/', CartaoList.as_view(), name='cartao-view'),
    path('cartoes/<int:cartao_id>/', CartaoDetails.as_view()),
    path('categorias/', CategoriasList.as_view(), name='categorias-list'),
    path('categorias/<int:categoria_id>/', CategoriasDetails.as_view(), name='categorias-details'),
    path('categorias/<int:categoria_id>/subcategorias/', SubcategoriaCategoria.as_view(), name='categoria_subcategoria'),
    path('categorias/tipo/<str:tipo>/', CategoriasTipo.as_view()),

    path('movimentacoes/ano/<int:ano>/mes/<int:mes>/', MovimentacaoDetails.as_view(), name='movimentacao-details'),

    path('subcategorias/', SubcategoriaList.as_view(), name='subcategoria-list'),
]
