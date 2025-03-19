from django.urls import include, path

from statement.views.portfolio.portfolio_views import *
from statement.views.portfolio.portfolio_views import PortfolioView

portfolio_view = PortfolioView()

urlpatterns = [
    path('', portfolio_view.get_portfolio, name='get_portfolio'),
    path('renda_fixa/', include('statement.urls.portfolio.fixed_income.fixed_income_urls')),
    path('renda_variavel/', include('statement.urls.portfolio.variable_income.variable_income')),
]
