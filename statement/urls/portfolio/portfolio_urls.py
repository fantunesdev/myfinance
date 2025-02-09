from django.urls import include, path

from statement.views.portfolio.portfolio_views import *

urlpatterns = [
    path('', get_portfolio, name='get_portfolio'),
    # path('cadastrar/', create_account, name='create_account'),
    # path('editar/<int:id>/', update_account, name='update_account'),
    # path('remover/<int:id>/', delete_account, name='delete_account'),

    path('renda_fixa/', include('statement.urls.portfolio.fixed_income.fixed_income_urls'))
]