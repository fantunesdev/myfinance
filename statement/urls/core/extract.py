"""
Extract é uma sub-view de TransactionsView e por isso não tem services e templates próprios. Os únicos templates
customizáveis para essa view são o dashboard e o navigation
"""

from django.urls import path

from statement.views.core.extract import ExtractView

extract_view = ExtractView()

urlpatterns = [
    path('', extract_view.get_current_month, name='get_current_month_extract_by_account'),
    path('mes_atual/', extract_view.get_current_month, name='get_current_month_extract_by_account'),
    path('<int:year>/', extract_view.get_by_year, name='get_extract_by_account_and_year'),
    path('<int:year>/<int:month>/', extract_view.get_by_year_and_month, name='get_extract_by_account_year_and_month'),
]
