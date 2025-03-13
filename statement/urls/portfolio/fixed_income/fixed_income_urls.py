from django.urls import include, path

from statement.views.portfolio.fixed_income.fixed_income_views import *

urlpatterns = [
    path('', list_fixed_income, name='list_fixed_income'),
    path('cadastrar/', create_fixed_income, name='create_fixed_income'),
    path('detalhar/<int:id>/', detail_fixed_income, name='detail_fixed_income'),
    path('editar/<int:id>/', update_fixed_income, name='update_fixed_income'),
    path('remover/<int:id>/', delete_fixed_income, name='delete_fixed_income'),
    path('instrumento/', include('statement.urls.portfolio.fixed_income.fixed_income_security_urls')),
]
