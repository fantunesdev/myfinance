from django.urls import path

from statement.views.portfolio.variable_income.ticker import TickerView

ticker_view = TickerView()

urlpatterns = [
    path('cadastrar/', ticker_view.create, name='create_ticker'),
    path('editar/<int:id>/', ticker_view.update, name='update_ticker'),
    path('remover/<int:id>/', ticker_view.delete, name='delete_ticker'),
]
