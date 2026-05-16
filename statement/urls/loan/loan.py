from django.urls import path

from statement.views.loan.loan import LoanView
from statement.views.loan.loan_entry import LoanEntryView

loan_view = LoanView()
loan_entry_view = LoanEntryView()

urlpatterns = [
    path('cadastrar/', loan_view.create, name='create_loan'),
    path('lancamentos/cadastrar/', loan_entry_view.create, name='create_loan_entry'),
    path('lancamentos/<int:id>/', loan_entry_view.detail, name='detail_loan_entry'),
    path('lancamentos/editar/<int:id>/', loan_entry_view.update, name='update_loan_entry'),
    path('lancamentos/remover/<int:id>/', loan_entry_view.delete, name='delete_loan_entry'),
    path('lancamentos/', loan_entry_view.get_all, name='get_all_loan_entry'),
    path('<int:id>/', loan_view.detail, name='detail_loan'),
    path('editar/<int:id>/', loan_view.update, name='update_loan'),
    path('remover/<int:id>/', loan_view.delete, name='delete_loan'),
    path('<str:status>/', loan_view.get_by_status, name='get_loans_by_status'),
    path('', loan_view.get_all, name='get_all_loan'),
]
