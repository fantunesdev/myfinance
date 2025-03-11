from statement.forms.portfolio.variable_income.sector import SectorForm
from statement.models import Sector
from statement.services.portfolio.variable_income.sector import SectorService
from statement.views.base_view import BaseView

class SectorView(BaseView):
    class_has_user = False
    class_title = 'setor'
    class_form = SectorForm
    model = Sector
    service = SectorService
    redirect_url = 'setup_settings'
