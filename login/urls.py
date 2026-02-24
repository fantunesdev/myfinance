from django.urls import path

from .views import *
from statement.views.next_month_view import edit_next_month_view
from statement.views.device import (
    create_device,
    get_all_device,
    detail_device,
    update_device,
    delete_device,
)

urlpatterns = [
    path('cadastrar/', create_user, name='create_user'),
    path('perfil/', get_profile, name='get_profile'),
    path('perfil/editar/', update_profile, name='update_profile'),
    path('perfil/configuracoes/editar/', update_configs, name='update_configs'),
    path('perfil/notificacoes/titles/editar/', edit_user_notification_titles, name='edit_user_notification_titles'),
    path('perfil/notificacoes/titles/', get_user_notification_titles, name='user_notification_titles'),
    path('perfil/next_month/editar/', edit_next_month_view, name='update_next_month_view'),
    path('alterar_senha/', change_password, name='change_password'),
    # Device management under user profile
    path('perfil/dispositivos/', get_all_device, name='get_all_device'),
    path('perfil/dispositivos/criar/', create_device, name='create_device'),
    path('perfil/dispositivos/<int:id>/', detail_device, name='detail_device'),
    path('perfil/dispositivos/<int:id>/editar/', update_device, name='update_device'),
    path('perfil/dispositivos/<int:id>/deletar/', delete_device, name='delete_device'),
]
