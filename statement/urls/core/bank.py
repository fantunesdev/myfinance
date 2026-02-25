from django.contrib.auth.decorators import user_passes_test
from django.urls import path

from statement.views.core.bank import BankView

bank_view = BankView()

staff_required = user_passes_test(lambda u: u.is_staff)

urlpatterns = [
    path('cadastrar/', staff_required(bank_view.create), name='create_bank'),
    path('editar/<int:id>/', staff_required(bank_view.update), name='update_bank'),
    path('remover/<int:id>/', staff_required(bank_view.delete), name='delete_bank'),
]
