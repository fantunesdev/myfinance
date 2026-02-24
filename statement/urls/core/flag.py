from django.urls import path
from django.contrib.auth.decorators import user_passes_test

from statement.views.core.flag import FlagView

flag_view = FlagView()

staff_required = user_passes_test(lambda u: u.is_staff)

urlpatterns = [
    path('cadastrar/', staff_required(flag_view.create), name='create_flag'),
    path('editar/<int:id>/', staff_required(flag_view.update), name='update_flag'),
    path('remover/<int:id>/', staff_required(flag_view.delete), name='delete_flag'),
]
