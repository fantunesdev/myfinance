from django.urls import include, path

from statement.views.transaction_views import *

urlpatterns = [
    path('', get_transactions, name='get_transactions'),
    path('<str:type>/cadastrar/', create_transaction, name='create_transaction'),
    path('ano/<int:year>/',get_transactions_by_year,name='get_transactions_by_year'),
    path('<int:year>/<int:month>/',get_transactions_by_year_and_month,name='get_transactions_by_year_and_month'),
    path('<int:year>/<int:month>/fixed',get_fixed_transactions_by_year_and_month,name='get_fixed_transactions_by_year_and_month'),
    path('<int:id>/', detail_transaction, name='detail_transaction'),
    path('mes_atual/',get_current_month_transactions,name='get_current_month_transactions'),
    path('importar/', import_transactions, name='import_transactions'),
    path('editar/<int:id>/', update_transaction, name='update_transaction'),
    path('remover/<int:id>', delete_transaction, name='delete_transaction'),
    path('pesquisa/descricao/<str:description>',get_transactions_by_description,name='get_transactions_by_description'),
    path('contas/<int:account_id>/extrato/',include('statement.urls.extract_urls')),
    path('cartoes/<int:card_id>/fatura/', include('statement.urls.invoice_urls')),
]
