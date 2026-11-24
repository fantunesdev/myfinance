from django.urls import include, path

from statement.views.settings_view import SettingsView

settings_view = SettingsView()

urlpatterns = [
    path('', settings_view.settings, name='setup_settings'),
    # Core
    path('bancos/', include('statement.urls.core.bank')),
    path('bandeiras/', include('statement.urls.core.flag')),
    path('cartoes/', include('statement.urls.core.card')),
    path('contas/', include('statement.urls.core.account')),
    path('categorias/', include('statement.urls.core.category')),
    path('subcategorias/', include('statement.urls.core.subcategory')),
    path('importacao_csv/', include('statement.urls.core.csv_import_config')),
    path('despesas_fixas/', include('statement.urls.core.fixed_expenses')),
    path('notificacoes/', include('statement.urls.core.notification')),
    path('appconfig/editar/', settings_view.edit_app_config, name='edit_app_config'),
    path('notifications/titles/edit/', settings_view.edit_notification_titles, name='edit_notification_titles'),
]
