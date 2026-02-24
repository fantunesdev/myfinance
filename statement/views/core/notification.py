from statement.forms.core.notification import NotificationForm
from statement.models import Notification
from statement.services.core.notification import NotificationService
from statement.views.base_view import BaseView
from statement.services.core.notification_title import NotificationTitleService


class NotificationView(BaseView):
    """
    View responsável pela gestão das notificações
    """

    class_has_user = True
    class_title = 'Notificação'
    class_form = NotificationForm
    model = Notification
    service = NotificationService
    # após operações CRUD, redirecionar para a lista de notificações
    redirect_url = 'get_all_notification'
    # use a custom template for the notifications list so we can add a back link
    template_is_global = {
        'create': True,
        'delete': True,
        'detail': True,
        'get_all': False,
        'update': True,
    }
    # Cabeçalhos das colunas para a listagem (correspondem aos campos do modelo Notification)
    column_names = ['Usuário', 'Aplicação', 'Título', 'Mensagem', 'Cartão', 'Usada', 'Criado em']
    # Campos a exibir na listagem (na mesma ordem dos cabeçalhos) — excluir `id`
    list_fields = ['user', 'app', 'title', 'message', 'card', 'is_used', 'created_at']

    def _add_context_on_templatetags(self, request, instance):
        """
        Ajusta o contexto para a listagem: se o usuário não for staff, remove a coluna
        "Usuário" e o campo `user` da lista de campos exibidos.
        """
        # Só precisa ajustar na listagem (get_all)
        if getattr(self, '_context', None) != 'get_all':
            return {}

        # Se for staff, manter todas as colunas (incluindo 'user'), senão removê-la
        if request.user and request.user.is_staff:
            new_fields = list(self.list_fields)
            new_column_names = list(self.column_names)
        else:
            # Copia as listas e remove o campo/coluna relacionado a usuário
            new_fields = [f for f in list(self.list_fields) if f != 'user']
            # column_names deve ser mantida na mesma ordem; mapeia por índice baseado em list_fields
            # Construir nova coluna_names removendo o índice onde list_fields == 'user'
            try:
                original_fields = list(self.list_fields)
                idx = original_fields.index('user')
                new_column_names = [c for i, c in enumerate(list(self.column_names)) if i != idx]
            except ValueError:
                new_column_names = list(self.column_names)

        extra = {
            'fields': new_fields,
            'column_names': new_column_names,
        }
        # Adiciona os títulos de notificação e o estado do usuário para a página de listagem
        try:
            NotificationTitleService.ensure_titles([])
            all_titles = NotificationTitleService.get_all_titles()
            enabled = NotificationTitleService.get_enabled_titles_for_user(request.user)
            extra['notification_titles'] = [
                {'id': nt.id, 'title': nt.title, 'enabled': (nt.title in enabled)} for nt in all_titles
            ]
        except Exception:
            extra['notification_titles'] = []

        return extra
