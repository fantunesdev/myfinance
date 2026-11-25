from django.urls import path

from login.password_reset import RecoveryCompleteView, RecoveryConfirmView, RecoveryDoneView, RecoveryRequestView

urlpatterns = [
    path('recuperar/', RecoveryRequestView.as_view(), name='password_reset'),
    path('recuperar/enviado/', RecoveryDoneView.as_view(), name='password_reset_done'),
    path('recuperar/<uidb64>/<token>/', RecoveryConfirmView.as_view(), name='password_reset_confirm'),
    path('recuperar/concluido/', RecoveryCompleteView.as_view(), name='password_reset_complete'),
]
