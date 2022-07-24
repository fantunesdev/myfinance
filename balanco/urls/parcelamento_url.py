from django.urls import path

from balanco.views.parcelamento_view import *

urlpatterns = [
    path('<int:id>/', detalhar_parcelamento, name='detalhar_parcelamento'),
    path('editar/<int:id>/', editar_parcelamento, name='editar_parcelamento'),
    path('adiantar_parcelas/<int:id>/', adiantar_parcelas, name='adiantar_parcelas'),
    path('remover/<int:id>/', remover_parcelamento, name='remover_parcelamento'),
    path('remover/parcela/<int:id>/', remover_parcela, name='remover_parcela')
]
