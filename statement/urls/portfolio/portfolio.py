from django.urls import include, path

from statement.views.portfolio.portfolio import PortfolioView

portfolio_view = PortfolioView()

urlpatterns = [
    path('', portfolio_view.get_portfolio, name='get_portfolio'),
    path('renda_fixa/', include('statement.urls.portfolio.fixed_income.fixed_income')),
    path('renda_variavel/', include('statement.urls.portfolio.variable_income.variable_income')),
]
