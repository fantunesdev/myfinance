from django.urls import include, path

from statement.views.settings_view import *

urlpatterns = [
    path('', setup_settings, name='setup_settings'),
    
    # Core
    path('bancos/', include('statement.urls.core.bank')),
    path('bandeiras/', include('statement.urls.core.flag')),
    path('cartoes/', include('statement.urls.core.card')),
    path('contas/', include('statement.urls.core.account')),
    path('categorias/', include('statement.urls.core.category')),
    path('subcategorias/', include('statement.urls.core.subcategory')),

    path('despesas_fixas/', include('statement.urls.fixed_expenses_urls')),
    path('parcelamento/', include('statement.urls.installment_urls')),

    # Renda Fixa
    path('indices/', include('statement.urls.portfolio.fixed_income.index_urls')),
    path('visualizacao_proximo_mes/',include('statement.urls.next_month_view_url')),

    # Renda Variável
    path('setor/', include('statement.urls.portfolio.variable_income.sector')),
    path('papel/', include('statement.urls.portfolio.variable_income.ticker')),
]
