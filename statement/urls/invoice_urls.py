from django.urls import path

from statement.views.core.card import CardView
from statement.views.invoice_view import *

card_view = CardView()

urlpatterns = [
    path('cadastrar/', card_view.create, name='create_card'),
    path('editar/<int:id>/', card_view.update, name='update_card'),
    path('remover/<int:id>/', card_view.delete, name='delete_card'),
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
