from django.urls import path
from django.contrib.auth.decorators import user_passes_test

from statement.views.core.account import AccountView

account_view = AccountView()

staff_required = user_passes_test(lambda u: u.is_staff)

urlpatterns = [
    path('cadastrar/', staff_required(account_view.create), name='create_account'),
    path('editar/<int:id>/', staff_required(account_view.update), name='update_account'),
    path('remover/<int:id>/', staff_required(account_view.delete), name='delete_account'),
]
