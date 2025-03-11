from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator

from statement.forms.dream.dream import DreamForm
from statement.models import Dream
from statement.services.dream.dream import DreamService
from statement.services.dream.portion import PortionService
from statement.views.base_view import BaseView

class DreamView(BaseView):
    """
    View responsável pela gestão das categorias
    """
    class_has_user = True
    class_title = 'Sonhos'
    class_form = DreamForm
    model = Dream
    service = DreamService
    redirect_url = reverse_lazy('get_dreams_by_status', args=['ativos'])

    def __init__(self):
        """
        Atualiza o dicionário template_is_global sem sobrescrever toda a estrutura da classe base.
        """
        super().__init__()
        self.template_is_global.update({
            'detail': False,
            'get_all': False,
        })

    @method_decorator(login_required)
    def get_by_status(self, request, status):
        if status == 'ativos':
            dreams = self.service.get_active_dreams(request.user)
        elif status == 'inativos':
            dreams = self.service.get_past_dreams(request.user)
        else:
            raise Http404("Status inválido")
        specific_content = {
            'instances': dreams
        }
        return self.render_form(request, None, 'dream/list.html', specific_content)

    def add_context_on_detail(self, request, instance):
        return {
            'portions': PortionService.get_portions_by_dream(instance.id, request.user),
        }
