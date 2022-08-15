from django.urls import path

from statement.views.transaction_views import *

urlpatterns = [
    path('', get_transactions, name='get_transactions'),
    path('<str:type>/cadastrar/', create_transaction, name='create_transaction'),
    path('ano/<int:year>/', get_transactions_by_year, name='get_transactions_by_year'),
    path('<int:year>/<int:month>/', get_transactions_by_year_and_month, name='get_transactions_by_year_and_month'),
    path('<int:id>/', detail_transaction, name='detail_transaction'),
    path('mes_atual/', get_current_month_transactions, name='get_current_month_transactions'),
    path('editar/<int:id>/', update_transaction, name='update_transaction'),
    path('remover/<int:id>', delete_transaction, name='delete_transaction')
]
