from django.urls import include, path

from statement.views.core.transaction import TransactionView
from statement.views.core.fixed_expenses import FixedExpensesView

transaction_view = TransactionView()
fixed_expenses_view = FixedExpensesView()

urlpatterns = [
    path('<str:type>/cadastrar/', transaction_view.create, name='create_transaction'),
    path('ano/<int:year>/', transaction_view.get_by_year, name='get_transactions_by_year'),
    path('<int:year>/<int:month>/', transaction_view.get_by_year_and_month, name='get_transactions_by_year_and_month'),
    path('<int:year>/<int:month>/fixed', fixed_expenses_view.get_by_year_and_month, name='get_fixed_transactions_by_year_and_month'),
    path('<int:id>/', transaction_view.detail, name='detail_transaction'),
    path('mes_atual/', transaction_view.get_current_month, name='get_current_month_transactions'),
    path('importar/', transaction_view.import_transactions, name='import_transactions'),
    path('editar/<int:id>/', transaction_view.update, name='update_transaction'),
    path('remover/<int:id>', transaction_view.delete, name='delete_transaction'),
    path('pesquisa/descricao/<str:description>', transaction_view.get_by_description, name='get_transactions_by_description'),
    path('contas/<int:id>/extrato/', include('statement.urls.core.extract')),
    path('cartoes/<int:id>/fatura/', include('statement.urls.core.invoice')),
    path('parcelamento/', include('statement.urls.core.installment')),
]
