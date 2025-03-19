from django.urls import path

from statement.views.core.fixed_expenses import FixedExpensesView

fixed_expenses_view = FixedExpensesView()

urlpatterns = [
    path('cadastrar/', fixed_expenses_view.create, name='create_fixed_expense'),
    path('editar/<int:id>/', fixed_expenses_view.update, name='update_fixed_expense'),
    path('remover/<int:id>/', fixed_expenses_view.delete, name='delete_fixed_expense'),
]
