from django.urls import path, include

from statement.views.card_views import *

urlpatterns = [
    path('cadastrar/', create_card, name='create_card'),
    path('editar/<int:id>/', update_card, name='update_card'),
    path('remover/<int:id>/', delete_card, name='delete_card'),

    path('<int:card_id>/fatura/', include('statement.urls.invoice_urls'))
]
