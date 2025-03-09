from django.urls import path

from statement.views.core.flag import FlagView

flag_view = FlagView()

urlpatterns = [
    path('cadastrar/', flag_view.create, name='create_flag'),
    path('editar/<int:id>/', flag_view.update, name='update_flag'),
    path('remover/<int:id>/', flag_view.delete, name='delete_flag'),
]
