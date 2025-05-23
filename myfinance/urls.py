"""
URL configuration for myfinance project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from login.views import *
from myfinance import settings
from statement.views.core.transaction import TransactionView

transaction_view = TransactionView()

urlpatterns = [
    path('', transaction_view.get_current_month),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('login/', login_user, name='login_user'),
    path('logout/', logout_user, name='logout_user'),
    path('carteira/', include('statement.urls.portfolio.portfolio_urls')),
    path('relatorio_financeiro/', include('statement.urls.statement')),
    path('sonhos/', include('statement.urls.dream.dream')),
    path('usuarios/', include('login.urls')),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
