from django.urls import path

from balanco.views.parcelamento_view import *

urlpatterns = [
    path('editar/<int:id>/', editar_parcelamento, name='editar_parcelamento'),
    path('remover/<int:id>/', remover_parcelamento, name='remover_parcelamento')
]
