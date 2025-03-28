from django.urls import path

from api.views.account_views import AccountsDetails, AccountsList
from api.views.authentication import AuthenticationView
from api.views.bank_views import BankDetails, BankList
from api.views.card_views import CardDetails, CardList
from api.views.category_views import CategoryDetails, CategoryList, CategoryType
from api.views.default_views import Defaults
from api.views.extract_views import ExtractByAccountYearAndMonth
from api.views.invoice_views import InvoiceByCardYearAndMonth
from api.views.next_month_view_view import NextMonthView
from api.views.portfolio.fixed_income_views import FixedIncomeProgressionList
from api.views.subcategoy_views import SubcategoriesByCategory, SubcategoryList
from api.views.transaction_views import TransactionsList, TransactionYear, TransactionByYearAndMonth, ImportTransactions

authentication_view = AuthenticationView()

urlpatterns = [
    # Perfil
    path('next_month_view/', NextMonthView.as_view(), name='next_month_view'),

    # Core
    path('accounts/', AccountsList.as_view()),
    path('accounts/<int:account_id>/', AccountsDetails.as_view()),
    path('banks/', BankList.as_view()),
    path('banks/<int:bank_id>/', BankDetails.as_view()),
    path('cards/', CardList.as_view(), name='card-list'),
    path('cards/<int:card_id>/', CardDetails.as_view(), name='card-details'),
    path('cards/<int:card_id>/invoice/<int:year>/<int:month>/', InvoiceByCardYearAndMonth.as_view()),
    path('categories/', CategoryList.as_view(), name='categories-list'),
    path('categories/<int:category_id>/', CategoryDetails.as_view(), name='categories-details'),
    path('categories/<int:category_id>/subcategories/', SubcategoriesByCategory.as_view()),
    path('categories/type/<str:type>/', CategoryType.as_view(), name='category-type'),
    path('transactions/', TransactionsList.as_view(), name='transactions'),
    path('transactions/year/<int:year>/', TransactionYear.as_view(), name='transaction-year'),
    path('transactions/year/<int:year>/month/<int:month>/', TransactionByYearAndMonth.as_view()),
    path('transactions/accounts/<int:account_id>/year/<int:year>/month/<int:month>/', ExtractByAccountYearAndMonth.as_view()),
    path('transactions/card/<int:card_id>/year/<int:year>/month/<int:month>/', InvoiceByCardYearAndMonth.as_view()),
    path('transactions/import/', ImportTransactions.as_view(), name='import-transactions'),
    path('transactions/', TransactionsList.as_view(), name='transactions-list'),
    path('subcategories/', SubcategoryList.as_view(), name='subcategory-list'),

    # Retorno de configurações default para o FrontEnd antes de autenticar
    path('defaults/', Defaults.as_view(), name='defaults'),

    # Portfolio
    path('fixed-income/progression/', FixedIncomeProgressionList.as_view(), name='fixed_income_progression'),

    # Autenticação JWT
    path('token/', authentication_view.get_token, name='get_token'),
]
