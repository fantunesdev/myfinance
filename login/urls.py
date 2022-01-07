from django.urls import path
from .views import *

urlpatterns = [
    path('cadastrar/', cadastrar_usuario, name='cadastrar_usuario'),
    path('logado/', logado, name='logado')
]
