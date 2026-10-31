from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from django.core.exceptions import ValidationError
from django.forms import model_to_dict
from investments.forms.investment import InvestmentForm
from investments.forms.transaction import InvestmentTransactionForm
from investments.models import Investment, InvestmentTransaction
from investments.services.investment import InvestmentService
from investments.services.transaction import InvestmentTransactionService
from rest_framework import status
from rest_framework.response import Response


class InvestmentApiView(BaseView):
    serializer = BaseSerializer
    class_has_user = True

    def _save_form(self, request, instance=None, partial=False):
        data = model_to_dict(instance, fields=list(self.form_class.base_fields)) if partial else {}
        data.update(request.data)
        protected = {
            'operation_id',
            'statement_transaction',
            'funding_transaction',
            'redemption_principal',
            'default_wallet_for',
        }
        if protected.intersection(request.data) or ('user' in data and str(data['user']) != str(request.user.pk)):
            return Response(
                {'detail': 'Campos de proprietário e vínculos internos não podem ser alterados.'}, status=400
            )
        form = self.form_class(data, instance=instance, user=request.user)
        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            saved = self.service.update(form, instance) if instance else self.service.create(form, request.user)
        except ValidationError as error:
            return Response({'detail': error.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._get_serializer(saved).data, status=200 if instance else 201)

    def create(self, request):
        return self._save_form(request)

    def update(self, request, pk=None):
        try:
            instance = self.service.get_by_id(pk, request.user)
        except self.model.DoesNotExist:
            return Response({'detail': 'Registro não encontrado.'}, status=404)
        return self._save_form(request, instance)

    def partial_update(self, request, pk=None):
        try:
            instance = self.service.get_by_id(pk, request.user)
        except self.model.DoesNotExist:
            return Response({'detail': 'Registro não encontrado.'}, status=404)
        return self._save_form(request, instance, partial=True)

    def destroy(self, request, pk=None):
        try:
            instance = self.service.get_by_id(pk, request.user)
        except self.model.DoesNotExist:
            return Response({'detail': 'Registro não encontrado.'}, status=404)
        try:
            self.service.delete(instance)
        except ValidationError as error:
            return Response({'detail': error.messages}, status=400)
        return Response(status=204)


class InvestmentView(InvestmentApiView):
    model = Investment
    service = InvestmentService
    form_class = InvestmentForm


class InvestmentTransactionView(InvestmentApiView):
    model = InvestmentTransaction
    service = InvestmentTransactionService
    form_class = InvestmentTransactionForm
