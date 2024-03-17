from django.urls import path

from api.views.account_views import *
from api.views.bank_views import *
from api.views.card_views import *
from api.views.category_views import *
from api.views.default_views import *
from api.views.extract_views import *
from api.views.invoice_views import *
from api.views.next_month_view_view import NextMonthView
from api.views.subcategoy_views import *
from api.views.transaction_views import *

urlpatterns = [
    path('next_month_view/', NextMonthView.as_view(), name='next_month_view'),
    path('accounts/', AccountsList.as_view()),
    path('accounts/<int:account_id>/', AccountsDetails.as_view()),
    path('banks/', BankList.as_view()),
    path('banks/<int:bank_id>/', BankDetails.as_view()),
    path('cards/', CardList.as_view(), name='card-list'),
    path('cards/<int:card_id>/', CardDetails.as_view(), name='card-details'),
    path(
        'cards/<int:card_id>/invoice/<int:year>/<int:month>/',
        InvoiceByCardYearAndMonth.as_view(),
    ),
    path('categories/', CategoryList.as_view(), name='categories-list'),
    path(
        'categories/<int:category_id>/',
        CategoryDetails.as_view(),
        name='categories-details',
    ),
    path(
        'categories/<int:category_id>/subcategories/',
        SubcategoriesByCategory.as_view(),
    ),
    path(
        'categories/type/<str:type>/',
        CategoryType.as_view(),
        name='category-type',
    ),
    path(
        'transactions/year/<int:year>/',
        TransactionYear.as_view(),
        name='transaction-year',
    ),
    path(
        'transactions/year/<int:year>/month/<int:month>/',
        TransactionByYearAndMonth.as_view(),
    ),
    path('transactions/year/<int:year>/',TransactionsByYear.as_view()),
    path(
        'transactions/accounts/<int:account_id>/year/<int:year>/month/<int:month>/',
        ExtractByAccountYearAndMonth.as_view(),
    ),
    path(
        'transactions/card/<int:card_id>/year/<int:year>/month/<int:month>/',
        InvoiceByCardYearAndMonth.as_view(),
    ),
    path(
        'transactions/import/',
        ImportTransactions.as_view(),
        name='import-transactions',
    ),
    path(
        'transactions/', TransactionsList.as_view(), name='transactions-list'
    ),
    path('subcategories/', SubcategoryList.as_view(), name='subcategory-list'),
    path('defaults/', Defaults.as_view(), name='defaults'),
]
