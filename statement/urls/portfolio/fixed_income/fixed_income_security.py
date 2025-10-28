from django.urls import include, path

from statement.views.portfolio.fixed_income.security import FixedIncomeSecurityView

security_view = FixedIncomeSecurityView()

urlpatterns = [
    path('cadastrar/', security_view.create, name='create_fixed_income_security'),
    path('editar/<int:id>/', security_view.update, name='update_fixed_income_security'),
    path('remover/<int:id>/', security_view.delete, name='delete_fixed_income_security'),
]
