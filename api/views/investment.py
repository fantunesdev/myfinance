from rest_framework import status
from rest_framework.response import Response

from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from investments.forms.transaction import InvestmentTransactionForm
from investments.models import Investment, InvestmentTransaction
from investments.services.investment import InvestmentService
from investments.services.transaction import InvestmentTransactionService


class InvestmentView(BaseView):
    model = Investment
    service = InvestmentService
    serializer = BaseSerializer
    class_has_user = True


class InvestmentTransactionView(BaseView):
    model = InvestmentTransaction
    service = InvestmentTransactionService
    serializer = BaseSerializer
    class_has_user = True

    def create(self, request):
        form = InvestmentTransactionForm(request.data, user=request.user)

        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        instance = self.service.create(form, request.user)
        serialized_instance = self._get_serializer(instance)
        return Response(serialized_instance.data, status=status.HTTP_201_CREATED)
