from django.urls import path, include

urlpatterns = [
    path('', include('statement.urls.transaction_urls')),
    path('configuracoes/', include('statement.urls.settings_urls')),
]
