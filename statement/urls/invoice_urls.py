from django.urls import path

from statement.views.card_views import *
from statement.views.invoice_view import *

urlpatterns = [
    path('cadastrar/', create_card, name='create_card'),
    path('editar/<int:id>/', update_card, name='update_card'),
    path('remover/<int:id>/', delete_card, name='delete_card'),
    path(
        'mes_atual/',
        get_current_month_invoice_by_card,
        name='get_current_month_invoice_by_card',
    ),
    path(
        '<int:year>/<int:month>/',
        get_invoice_by_card_year_and_month,
        name='get_invoice_by_card_year_and_month',
    ),
]
