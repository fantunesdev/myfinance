from django.urls import path

from statement.views.dream.portion import PortionView

portion_view = PortionView()

urlpatterns = [
    path('', portion_view.get_all, name='get_portions'),
    path('<int:id>/', portion_view.detail, name='detail_portion'),
    path('cadastrar/', portion_view.create, name='create_portion'),
    path('editar/<int:id>/', portion_view.update, name='update_portion'),
    path('remover/<int:id>/', portion_view.delete, name='delete_portion'),
]
