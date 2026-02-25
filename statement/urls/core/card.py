from django.contrib.auth.decorators import user_passes_test
from django.urls import path

from statement.views.core.card import CardView

card_view = CardView()

staff_required = user_passes_test(lambda u: u.is_staff)

urlpatterns = [
    path('cadastrar/', staff_required(card_view.create), name='create_card'),
    path('editar/<int:id>/', staff_required(card_view.update), name='update_card'),
    path('remover/<int:id>/', staff_required(card_view.delete), name='delete_card'),
]
