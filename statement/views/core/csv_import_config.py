from statement.forms.core.csv_import_config import CSVImportConfigForm
from statement.models import CSVImportConfig
from statement.services.core.csv_import_config import CSVImportConfigService
from statement.views.base_view import BaseView


class CSVImportConfigView(BaseView):
    """
    View responsável pela gestão de configurações de importação CSV.
    """

    class_has_user = True
    class_title = 'Configuração de CSV'
    class_form = CSVImportConfigForm
    column_names = [
        'Nome',
        'Destino',
        'Data',
        'Descrição',
        'Valor',
        'Parcela',
        'Formato da Parcela',
        'Meio',
        'Conta',
        'Cartão',
    ]
    list_fields = [
        'name',
        'target_model',
        'date_column',
        'description_column',
        'value_column',
        'installment_column',
        'installment_format',
        'payment_method',
        'account',
        'card',
    ]
    model = CSVImportConfig
    service = CSVImportConfigService
    redirect_url = 'get_all_csv_import_config'
    show_duplicate_checker = False

    def __init__(self):
        super().__init__()
        self.snake_case_classname = 'csv_import_config'

    def _set_form(self, request, instance):
        if request.method == 'POST':
            return self.class_form(request.user, request.POST, request.FILES or None, instance=instance)
        return self.class_form(request.user, instance=instance)
