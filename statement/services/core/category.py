from api.services.websocket_services import send_websocket_update
from statement.models import Category
from statement.services.base_service import BaseService


class CategoryService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Category."""

    model = Category
    user_field = None

    @classmethod
    def get_all(cls, user=None):
        return super().get_all(user).order_by('description')

    @classmethod
    def create(cls, form, user=None, id=None):
        category = super().create(form)
        cls.send_category_update()
        return category

    @classmethod
    def get_by_type(cls, type):
        """Obtém categorias por tipo (entrada/saída), em ordem alfabética."""
        return cls.model.objects.filter(type=type).order_by('description')

    @classmethod
    def update(cls, form, instance):
        instance = super().update(form, instance)
        cls.send_category_update()
        return instance

    @classmethod
    def delete(cls, instance):
        super().delete(instance)
        cls.send_category_update()

    @classmethod
    def send_category_update(cls):
        """Envia a atualização das categorias via WebSocket."""
        send_websocket_update('categories', cls.get_all())
