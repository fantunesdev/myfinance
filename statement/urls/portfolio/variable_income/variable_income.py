from django.urls import path

from statement.views.portfolio.variable_income.variable_income import VariableIncomeView

variable_income_view = VariableIncomeView()

urlpatterns = [
    path('', variable_income_view.get_all, name='get_variable_income'),
    path('cadastrar/', variable_income_view.create, name='create_variable_income'),
    path('editar/<int:id>/', variable_income_view.update, name='update_variable_income'),
    path('remover/<int:id>/', variable_income_view.delete, name='delete_variable_income'),
]
