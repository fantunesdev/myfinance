from django.urls import path

from .views import *

urlpatterns = [
    path('cadastrar/', create_user, name='create_user'),
    path('perfil/', get_profile, name='get_profile'),
    path('perfil/editar/', update_profile, name='update_profile'),
    path('perfil/configuracoes/editar/', update_configs, name='update_configs'),
    path('alterar_senha/', change_password, name='change_password'),
]
