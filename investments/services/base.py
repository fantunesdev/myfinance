from investments.events import investment_atomic
from statement.services.base_service import BaseService


class InvestmentBaseService(BaseService):
    user_field = 'user'

    @classmethod
    @investment_atomic()
    def create(cls, form, user=None, id=None):
        return super().create(form, user=user, id=id)

    @classmethod
    @investment_atomic()
    def update(cls, form, instance):
        return super().update(form, instance)

    @classmethod
    @investment_atomic()
    def delete(cls, instance):
        return super().delete(instance)
