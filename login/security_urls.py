from django.urls import path
from login import account_email, security_views

urlpatterns = [
    path('', security_views.overview, name='account_security'),
    path('confirmar-identidade/', security_views.reauthenticate, name='security_reauthenticate'),
    path('2fa/confirmar/', security_views.challenge, name='two_factor_challenge'),
    path('2fa/configurar/', security_views.setup, name='two_factor_setup'),
    path('2fa/gerenciar/', security_views.manage_factor, name='two_factor_manage'),
    path('email/', account_email.request_change, name='change_account_email'),
    path('email/cancelar/', account_email.cancel_change, name='cancel_account_email'),
    path('email/confirmar/<str:token>/', account_email.confirm_change, name='confirm_account_email'),
]
