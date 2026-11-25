from django.urls import include, path

from statement.views.dream.dream import DreamView

dream_view = DreamView()

urlpatterns = [
    path('cadastrar/', dream_view.create, name='create_dream'),
    path('<int:id>/', dream_view.detail, name='detail_dream'),
    path('<int:id>/documentos/', dream_view.upload_documents, name='upload_dream_documents'),
    path('<int:id>/documentos/<int:document_id>/', dream_view.document, name='dream_document'),
    path('<int:id>/documentos/<int:document_id>/remover/', dream_view.delete_document, name='delete_dream_document'),
    path('<int:id>/fotos/', dream_view.upload_photos, name='upload_dream_photos'),
    path('<int:id>/fotos/ordenar/', dream_view.reorder_photos, name='reorder_dream_photos'),
    path('<int:id>/fotos/<int:photo_id>/', dream_view.photo, name='dream_photo'),
    path('<int:id>/fotos/<int:photo_id>/remover/', dream_view.delete_photo, name='delete_dream_photo'),
    path('editar/<int:id>/', dream_view.update, name='update_dream'),
    path('remover/<int:id>/', dream_view.delete, name='delete_dream'),
    path('parcelas/', include('statement.urls.dream.portion')),
    path('<int:id>/parcelas/', include('statement.urls.dream.portion')),
    path('<str:status>/', dream_view.get_by_status, name='get_dreams_by_status'),
    path('', dream_view.get_all, name='get_dreams'),
]
