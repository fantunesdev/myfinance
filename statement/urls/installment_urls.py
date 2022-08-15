from django.urls import path

from statement.views.installment_views import *

urlpatterns = [
    path('<int:id>/', detail_installment, name='detail_installment'),
    path('editar/<int:id>/', update_installment, name='update_installment'),
    path('adiantar_parcelas/<int:id>/', advance_installments, name='advance_installments'),
    path('remover/<int:id>/', delete_installment, name='delete_installment'),
    path('remover/parcela/<int:id>/', delete_parcel, name='delete_parcel')
]
