from django.urls import include, path

urlpatterns = [
    path('', include('statement.urls.core.transaction')),
    path('configuracoes/', include('statement.urls.settings_urls')),
    path('dashboards/', include('statement.urls.dashboards_urls')),
]
