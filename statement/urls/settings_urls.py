from django.urls import path, include

from statement.views.settings_view import *

urlpatterns = [
    path('', setup_settings, name='setup_settings'),
    path('bancos/', include('statement.urls.bank_urls')),
    path('bandeiras/', include('statement.urls.flag_urls')),
    path('cartoes/', include('statement.urls.card_urls')),
    path('categorias/', include('statement.urls.category_urls')),
    path('contas/', include('statement.urls.account_urls')),
    path('parcelamento/', include('statement.urls.installment_urls')),
    path('subcategorias/', include('statement.urls.subcategory_urls')),
    path('visualizacao_proximo_mes/', include('statement.urls.next_month_view_url')),

    path('importarrr/', importar_banco, name='importar_banco'),
]
