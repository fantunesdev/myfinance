from django.urls import path

from statement.views.portfolio.fixed_income.index import IndexView

index_view = IndexView()

urlpatterns = [
    path('cadastrar/', index_view.create, name='create_index'),
    path('editar/<int:id>/', index_view.update, name='update_index'),
    path('remover/<int:id>/', index_view.delete, name='delete_index'),
]
