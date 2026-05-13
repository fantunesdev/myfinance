from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator

from statement.forms.dream.dream import DreamForm
from statement.models import Dream
from statement.services.dream.dream import DreamService
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
        self.template_is_global.update(
            {
                'detail': False,
                'get_all': False,
                'update': False,
            }
        )

    @method_decorator(login_required)
    def get_by_status(self, request, status):
        """
        Obtem sonhos de acordo com o status.

        Status não é um atributo do model, ele é definido pela data atual.
        """
        if status == 'ativos':
            dreams = self.service.get_active_dreams(request.user)
        elif status == 'inativos':
            dreams = self.service.get_past_dreams(request.user)
        else:
            raise Http404('Status inválido')
        specific_content = {'instances': dreams}
        return self._render(request, None, 'dream/list.html', specific_content)

    def _add_context_on_templatetags(self, request, instance):
        """
        Retorna as transações relacionadas ao sonho.
        A partir de agora, apenas Transactions são usadas (não mais Portion).
        """
        return {
            'transactions': instance.transactions.filter(user=request.user).order_by('-posted_date'),
        }
