from django.urls import path

from statement.views.core.installment import InstallmentView

installment_view = InstallmentView()

urlpatterns = [
    path('<int:id>/', installment_view.detail, name='detail_installment'),
    path('editar/<int:id>/', installment_view.update, name='update_installment'),
    path('adiantar_parcelas/<int:id>/', installment_view.advance_transactions, name='advance_installments'),
    path('remover/<int:id>/', installment_view.delete, name='delete_installment'),
    path('remover/parcela/<int:id>/', installment_view.delete, name='delete_parcel'),
]
