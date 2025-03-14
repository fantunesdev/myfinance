"""
Invoice é uma sub-view de TransactionsView e por isso não tem services e templates próprios. Os únicos templates
customizáveis para essa view são o dashboard e o navigation
"""

from django.urls import path

from statement.views.core.invoice import InvoiceView

invoice_view = InvoiceView()

urlpatterns = [
    path('', invoice_view.get_current_month, name='get_current_month_invoice_by_card'),
    path('mes_atual/', invoice_view.get_current_month, name='get_current_month_invoice_by_card'),
    path('<int:year>/', invoice_view.get_by_year, name='get_invoice_by_card_and_year'),
    path('<int:year>/<int:month>/', invoice_view.get_by_year_and_month, name='get_invoice_by_card_year_and_month'),
]
