from django.urls import path

from statement.views.core.card import CardView

card_view = CardView()

urlpatterns = [
    path('cadastrar/', card_view.create, name='create_card'),
    path('editar/<int:id>/', card_view.update, name='update_card'),
    path('remover/<int:id>/', card_view.delete, name='delete_card'),
]
