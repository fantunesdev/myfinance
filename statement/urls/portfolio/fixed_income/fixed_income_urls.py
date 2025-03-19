from django.urls import include, path

from statement.views.portfolio.fixed_income.fixed_income import FixedIncomeView

fixed_income_view = FixedIncomeView()

urlpatterns = [
    path('', fixed_income_view.get_all, name='list_fixed_income'),
    path('cadastrar/', fixed_income_view.create, name='create_fixed_income'),
    path('detalhar/<int:id>/', fixed_income_view.detail, name='detail_fixed_income'),
    path('editar/<int:id>/', fixed_income_view.update, name='update_fixed_income'),
    path('remover/<int:id>/', fixed_income_view.delete, name='delete_fixed_income'),
    path('instrumento/', include('statement.urls.portfolio.fixed_income.fixed_income_security_urls')),
]
