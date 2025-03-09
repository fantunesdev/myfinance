from django.urls import path

from statement.views.core.bank import BankView

bank_view = BankView()

urlpatterns = [
    path('cadastrar/', bank_view.create, name='create_bank'),
    path('editar/<int:id>/', bank_view.update, name='update_bank'),
    path('remover/<int:id>/', bank_view.delete, name='delete_bank'),
]
