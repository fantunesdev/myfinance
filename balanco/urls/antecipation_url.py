from django.urls import path

from balanco.views.antecipation_view import *

urlpatterns = [
    path('create/', create_antecipation, name='create_antecipation'),
    path('update/', update_antecipation, name='update_antecipation')
]
