from django.urls import path

from api.views.cartao_views import *
from api.views.categoria_views import *
from api.views.subcategoria_views import *

urlpatterns = [
    path('cartoes/', CartaoList.as_view()),
    path('cartoes/<int:cartao_id>/', CartaoDetails.as_view()),

    path('categorias/', CategoriasList.as_view(), name='categorias-list'),
    path('categorias/<int:categoria_id>/', CategoriasDetails.as_view(), name='categorias-details'),
    path('categorias/<int:categoria_id>/subcategorias/', SubcategoriaCategoria.as_view(), name='categoria_subcategoria'),
    path('categorias/tipo/<str:tipo>/', CategoriasTipo.as_view()),

    path('subcategorias/', SubcategoriaList.as_view(), name='subcategoria-list'),
]
