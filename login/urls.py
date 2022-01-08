from django.urls import path
from .views import *

urlpatterns = [
    path('cadastrar/', cadastrar_usuario, name='cadastrar_usuario'),
    path('perfil/', editar_perfil, name='editar_perfil'),
    path('alterar_senha/', alterar_senha, name='alterar_senha'),
    path('logado/', logado, name='logado')
]
