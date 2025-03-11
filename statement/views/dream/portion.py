from django.urls import reverse_lazy

from statement.forms.dream.portion import PortionForm
from statement.models import Portion
from statement.services.dream.portion import PortionService
from statement.views.base_view import BaseView

class PortionView(BaseView):
    """
    View responsável pela gestão das categorias
    """
    class_has_user = True
    class_title = 'Parcelas'
    class_form = PortionForm
    model = Portion
    service = PortionService
    redirect_url = reverse_lazy('get_dreams_by_status', args=['ativos'])
