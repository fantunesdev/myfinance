"""financeiro URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
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
from django.urls import path, include

from financeiro import settings
from login.views import *
from statement.views.transaction_views import get_current_month_transactions

urlpatterns = [
    path('', get_current_month_transactions),

    path('admin/', admin.site.urls),

    path('api/', include('api.urls')),

    # path('next_month_view/', include('balanco.urls.antecipation_url')),
    # path('banco/', include('balanco.urls.banco_url')),
    # path('bandeira/', include('balanco.urls.bandeira_url')),
    # path('balanco/configurar/', configurar, name='configurar'),
    # path('cartao/', include('balanco.urls.cartao_url')),
    # path('categoria/', include('balanco.urls.categoria_url')),
    # path('conta/', include('balanco.urls.conta_url')),
    # path('movimentacao/', include('balanco.urls.movimentacao_url')),
    # path('parcelamento/', include('balanco.urls.parcelamento_url')),
    # path('subcategoria/', include('balanco.urls.subcategoria_url')),

    path('relatorio_financeiro/', include('statement.urls.statement_urls')),

    path('usuarios/', include('login.urls')),
    path('login/', login_user, name='login_user'),
    path('logout/', logout_user, name='logout_user'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
