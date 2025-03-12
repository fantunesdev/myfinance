from statement.services.base_service import BaseService
from statement.services.dream.dream import DreamService
from statement.models import Portion


class PortionService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Portion."""
    model = Portion
    user_field = 'user'
    parent_service = DreamService
    parent_class_field = 'dream'

    @classmethod
    def create(cls, form, user=None, id=None):
        if id:
            instance = form.save(commit=False)
            instance.dream = DreamService.get_by_id(id, user=user)
        return super().create(form, user, id)

    @classmethod
    def get_portions_by_dream(cls, dream, user):
        return Portion.objects.filter(dream=dream, user=user)

    @classmethod
    def calculate_remaining_value(cls, dream_id, dream_value, user):
        portions = cls.get_portions_by_dream(dream_id, user)
        total_paid = sum(portion.value for portion in portions)
        remaining_value = dream_value - total_paid
        return remaining_value
