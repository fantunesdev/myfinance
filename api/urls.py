from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter

from api.views.authentication import AuthenticationView
from api.views.default_views import Defaults
from api.views.extract_views import ExtractByAccountYearAndMonth
from api.views.invoice_views import InvoiceByCardYearAndMonth
from api.views.next_month_view_view import NextMonthView
from api.views.portfolio.fixed_income_views import FixedIncomeProgressionList
from api.views.subcategory import SubcategoryView
from api.views.account import AccountView
from api.views.bank import BankView
from api.views.card import CardView
from api.views.category import CategoryView
from api.views.transaction_views import (
    ImportTransactions,
    TransactionByYearAndMonth,
    TransactionsList,
    TransactionView,
    TransactionYear,
)

authentication_view = AuthenticationView()
transaction_view = TransactionView()

router = DefaultRouter()
router.register(r'subcategories', SubcategoryView, basename='subcategory')
router.register(r'categories', CategoryView, basename='category')
router.register(r'accounts', AccountView, basename='account')
router.register(r'banks', BankView, basename='banks')
router.register(r'cards', CardView, basename='cards')

urlpatterns = [
    path('', include(router.urls)),
    path('categories/<str:type>/', SubcategoryView.as_view({'get': 'get_by_type'})),

    # Perfil
    path('next_month_view/', NextMonthView.as_view(), name='next_month_view'),

    # Core
    path('transactions/', TransactionsList.as_view(), name='transactions'),
    path('transactions/year/<int:year>/', TransactionYear.as_view(), name='transaction-year'),
    path('transactions/year/<int:year>/month/<int:month>/', TransactionByYearAndMonth.as_view()),
    path('transactions/accounts/<int:account_id>/year/<int:year>/month/<int:month>/', ExtractByAccountYearAndMonth.as_view()),
    path('transactions/cards/<int:card_id>/year/<int:year>/month/<int:month>/', InvoiceByCardYearAndMonth.as_view()),
    path('transactions/import/', ImportTransactions.as_view(), name='import-transactions'),
    path('transactions/', transaction_view.get_all, name='get_transactions'),

    # Retorno de configurações default para o FrontEnd antes de autenticar
    path('defaults/', Defaults.as_view(), name='defaults'),

    # Portfolio
    path('fixed-income/progression/', FixedIncomeProgressionList.as_view(), name='fixed_income_progression'),

    # Autenticação JWT
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
