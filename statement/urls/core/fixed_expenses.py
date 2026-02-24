from django.urls import path
from django.contrib.auth.decorators import user_passes_test

from statement.views.core.fixed_expenses import FixedExpensesView

fixed_expenses_view = FixedExpensesView()

staff_required = user_passes_test(lambda u: u.is_staff)

urlpatterns = [
    path('cadastrar/', staff_required(fixed_expenses_view.create), name='create_fixed_expense'),
    path('editar/<int:id>/', staff_required(fixed_expenses_view.update), name='update_fixed_expense'),
    path('remover/<int:id>/', staff_required(fixed_expenses_view.delete), name='delete_fixed_expense'),
    # backward-compatible alias (some templates/code expect plural name)
    path('remover/<int:id>/', staff_required(fixed_expenses_view.delete), name='delete_fixed_expenses'),
]
