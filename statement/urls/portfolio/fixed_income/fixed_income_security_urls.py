from django.urls import include, path

from statement.views.portfolio.fixed_income.security_views import *

urlpatterns = [
    path('cadastrar/', create_fixed_income_security, name='create_fixed_income_security'),
    path('editar/<int:id>/', update_fixed_income_security, name='update_fixed_income_security'),
    path('remover/<int:id>/', delete_fixed_income_security, name='delete_fixed_income_security'),
]
