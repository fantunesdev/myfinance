from django.urls import path

from statement.views.core.csv_import_config import CSVImportConfigView

csv_import_config_view = CSVImportConfigView()

urlpatterns = [
    path('', csv_import_config_view.get_all, name='get_all_csv_import_config'),
    path('cadastrar/', csv_import_config_view.create, name='create_csv_import_config'),
    path('<int:id>/', csv_import_config_view.detail, name='detail_csv_import_config'),
    path('editar/<int:id>/', csv_import_config_view.update, name='update_csv_import_config'),
    path('remover/<int:id>/', csv_import_config_view.delete, name='delete_csv_import_config'),
]
