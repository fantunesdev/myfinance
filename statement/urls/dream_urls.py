from django.urls import include, path

from statement.views.dream_views import *
from statement.views.portion_views import *

urlpatterns = [
    path('cadastrar/', create_dream, name='create_dream'),
    path('', list_dreams, name='list_dreams'),
    path('<int:id>', detail_dream, name='detail_dream'),
    path('editar/<int:id>/', update_dream, name='update_dream'),
    path('remover/<int:id>/', delete_dream, name='delete_dream'),

    path('<int:id_dream>/parcelas/cadastrar/', create_portion, name='create_portion'),
    path('<int:id_dream>/parcelas/editar/<int:id>/', update_portion, name='update_portion'),
    path('<int:id_dream>/parcelas/remover/<int:id>/', delete_portion, name='delete_portion'),
]
