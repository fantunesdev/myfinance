from django.urls import path

from investments.views.asset import AssetView
from investments.views.broker import BrokerView
from investments.views.dashboard import InvestmentsDashboardView
from investments.views.investment import InvestmentView
from investments.views.transaction import InvestmentTransactionView

asset_view = AssetView()
broker_view = BrokerView()
dashboard_view = InvestmentsDashboardView()
investment_view = InvestmentView()
transaction_view = InvestmentTransactionView()

urlpatterns = [
    path('', dashboard_view.dashboard, name='investments_dashboard'),
    path('brokers/cadastrar/', broker_view.create, name='create_broker'),
    path('brokers/<int:id>/', broker_view.detail, name='detail_broker'),
    path('brokers/editar/<int:id>/', broker_view.update, name='update_broker'),
    path('brokers/remover/<int:id>/', broker_view.delete, name='delete_broker'),
    path('brokers/', broker_view.get_all, name='get_all_broker'),
    path('ativos/cadastrar/', asset_view.create, name='create_asset'),
    path('ativos/<int:id>/', asset_view.detail, name='detail_asset'),
    path('ativos/editar/<int:id>/', asset_view.update, name='update_asset'),
    path('ativos/remover/<int:id>/', asset_view.delete, name='delete_asset'),
    path('ativos/', asset_view.get_all, name='get_all_asset'),
    path('investimentos/cadastrar/', investment_view.create, name='create_investment'),
    path('investimentos/<int:id>/', investment_view.detail, name='detail_investment'),
    path('investimentos/editar/<int:id>/', investment_view.update, name='update_investment'),
    path('investimentos/remover/<int:id>/', investment_view.delete, name='delete_investment'),
    path('investimentos/', investment_view.get_all, name='get_all_investment'),
    path('movimentacoes/cadastrar/', transaction_view.create, name='create_investment_transaction'),
    path('movimentacoes/<int:id>/', transaction_view.detail, name='detail_investment_transaction'),
    path('movimentacoes/editar/<int:id>/', transaction_view.update, name='update_investment_transaction'),
    path('movimentacoes/remover/<int:id>/', transaction_view.delete, name='delete_investment_transaction'),
    path('movimentacoes/', transaction_view.get_all, name='get_all_investment_transaction'),
]
