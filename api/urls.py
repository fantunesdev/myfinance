from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api.views.account import AccountView
from api.views.bank import BankView
from api.views.card import CardView
from api.views.categorization_feedback import CategorizationFeedbackView
from api.views.category import CategoryView
from api.views.default_views import Defaults
from api.views.next_month_view_view import NextMonthView
from api.views.portfolio.fixed_income_views import FixedIncomeProgressionList
from api.views.subcategory import SubcategoryView
from api.views.transaction import TransactionView
from api.views.transaction_classifier import TransactionClassifierView
from api.views.validate_token import ValidateTokenView

router = DefaultRouter()
router.register(r'subcategories', SubcategoryView, basename='subcategory')
router.register(r'categories', CategoryView, basename='category')
router.register(r'categorization-feedback', CategorizationFeedbackView, basename='categorization_feedback')
router.register(r'accounts', AccountView, basename='account')
router.register(r'banks', BankView, basename='banks')
router.register(r'cards', CardView, basename='cards')
router.register(r'transactions', TransactionView, basename='transactions')
router.register(r'transaction-classifier', TransactionClassifierView, basename='transaction_classifier')

urlpatterns = [
    path('', include(router.urls)),
    # Perfil
    path('next_month_view/', NextMonthView.as_view(), name='next_month_view'),
    # Retorno de configurações default para o FrontEnd antes de autenticar
    path('defaults/', Defaults.as_view(), name='defaults'),
    # Portfolio
    path('fixed-income/progression/', FixedIncomeProgressionList.as_view(), name='fixed_income_progression'),
    # Autenticação JWT
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('validate-token/', ValidateTokenView.as_view(), name='validate_token')
]
