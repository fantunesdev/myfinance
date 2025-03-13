from django.urls import include, path

from statement.views.portfolio.portfolio_views import *

urlpatterns = [
    path('', get_portfolio, name='get_portfolio'),
    path('renda_fixa/', include('statement.urls.portfolio.fixed_income.fixed_income_urls')),
    path('renda_variavel/', include('statement.urls.portfolio.variable_income.variable_income')),
]
