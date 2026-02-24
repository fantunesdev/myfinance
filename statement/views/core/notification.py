from statement.forms.core.notification import NotificationForm
from statement.models import Notification
from statement.services.core.notification import NotificationService
from statement.views.base_view import BaseView


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

        # Se for staff, nada a fazer
        if request.user and request.user.is_staff:
            return {}

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

        return {
            'fields': new_fields,
            'column_names': new_column_names,
        }
