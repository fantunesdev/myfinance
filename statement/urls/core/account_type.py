from django.urls import path
from django.contrib.auth.decorators import user_passes_test

from statement.views.core.account_type import AccountTypeView

account_type_view = AccountTypeView()

staff_required = user_passes_test(lambda u: u.is_staff)

urlpatterns = [
    path('cadastrar/', staff_required(account_type_view.create), name='create_account_type'),
    path('editar/<int:id>/', staff_required(account_type_view.update), name='update_account_type'),
    path('remover/<int:id>/', staff_required(account_type_view.delete), name='delete_account_type'),
]
