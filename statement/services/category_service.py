from api.services.websocket_services import send_websocket_update
from statement.services.base_service import BaseService
from statement.models import Category


class CategoryService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Category."""
    model = Category
    user_field = None

    @classmethod
    def create(cls, form, user=None):
        category = super().create(form)
        cls.send_category_update()
        return category

    @classmethod
    def get_by_type(cls, type):
        """Obtem categorias pilo tipo (entrada/saída)"""
        return cls.model.objects.filter(type=type)

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
