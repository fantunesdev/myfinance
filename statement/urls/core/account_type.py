from django.urls import path

from statement.views.core.account_type import AccountTypeView

account_type_view = AccountTypeView()

urlpatterns = [
    path('cadastrar/', account_type_view.create, name='create_account_type'),
    path('editar/<int:id>/', account_type_view.update, name='update_account_type'),
    path('remover/<int:id>/', account_type_view.delete, name='delete_account_type'),
]
