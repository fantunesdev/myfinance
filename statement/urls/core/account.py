from django.urls import path

from statement.views.core.account import AccountView

account_view = AccountView()

urlpatterns = [
    path('cadastrar/', account_view.create, name='create_account'),
    path('editar/<int:id>/', account_view.update, name='update_account'),
    path('remover/<int:id>/', account_view.delete, name='delete_account'),
]
