from django.urls import path

from balanco.views.parcelamento_view import *

urlpatterns = [
    path('remover/<int:id>/', remover_parcelamento, name='remover_parcelamento')
]
