from django.urls import path

from api.views.antecipation_views import *
from api.views.card_views import *
from api.views.category_views import *
from api.views.next_month_view_view import NextMonthView
from api.views.transaction_views import *
from api.views.subcategoy_views import *

urlpatterns = [
    path('antecipation/', Antecipation.as_view(), name='antecipation'),
    path('next_month_view/', NextMonthView.as_view(), name='next_month_view'),
    path('cartoes/', CardList.as_view(), name='card-list'),
    path('cartoes/<int:card_id>/', CardDetails.as_view(), name='card-details'),
    path('categorias/', CategoryList.as_view(), name='categories-list'),
    path('categorias/<int:category_id>/', CategoryDetails.as_view(), name='categories-details'),
    path('categorias/<int:category_id>/subcategorias/', SubcategoriesCategory.as_view(), name='subcategories-category'),
    path('categorias/tipo/<str:type>/', CategoryType.as_view(), name='category-type'),

    path('movimentacoes/ano/<int:year>/mes/<int:month>/', TransactionYearMonth.as_view(), name='transaction-year-month'),
    path('movimentacoes/ano/<int:year>/', TransactionYear.as_view(), name='transaction-year'),

    path('subcategorias/', SubcategoryList.as_view(), name='subcategory-list'),


    path('next_month_view/', NextMonthView.as_view(), name='next_month_view'),
]
