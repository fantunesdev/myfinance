from statement.forms.portfolio.fixed_income.index import IndexForm
from statement.models import Index
from statement.services.portfolio.fixed_income.index import IndexService
from statement.views.base_view import BaseView


class IndexView(BaseView):
    class_has_user = False
    class_title = 'papel'
    class_form = IndexForm
    model = Index
    service = IndexService
    redirect_url = 'setup_settings'
