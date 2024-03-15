from django.urls import path

from statement.views.fixed_expenses_views import *

urlpatterns = [
    path('cadastrar/', create_fixed_expense, name='create_fixed_expense'),
    path('editar/<int:id>/', update_fixed_expense, name='update_fixed_expense'),
    path('remover/<int:id>/', delete_fixed_expense, name='delete_fixed_expense'),
]
