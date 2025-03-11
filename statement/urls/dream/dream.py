from django.urls import path, include

from statement.views.dream.dream import DreamView

dream_view = DreamView()

urlpatterns = [
    path('cadastrar/', dream_view.create, name='create_dream'),
    path('<int:id>/', dream_view.detail, name='detail_dream'),
    path('editar/<int:id>/', dream_view.update, name='update_dream'),
    path('remover/<int:id>/', dream_view.delete, name='delete_dream'),
    path('<int:id>/parcelas/', include('statement.urls.dream.portion')),
    path('<str:status>/', dream_view.get_by_status, name='get_dreams_by_status'),
    path('', dream_view.get_all, name='get_dreams'),
]
