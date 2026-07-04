from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator

from investments.forms.investment import InvestmentCashMovementForm, InvestmentForm, InvestmentRedemptionForm
from investments.models import Investment
from investments.services.investment import InvestmentService
from investments.services.transaction import InvestmentTransactionService
from investments.views.base import InvestmentCrudView


class InvestmentView(InvestmentCrudView):
    class_title = 'Investimentos'
    class_form = InvestmentForm
    model = Investment
    service = InvestmentService
    redirect_url = reverse_lazy('investments_dashboard')
    column_names = ['Descrição', 'Ativo', 'Broker', 'Status']
    list_fields = ['description', 'asset', 'broker', 'status_label']

    def __init__(self):
        super().__init__()
        self.template_is_global.update({'detail': False})

    def _add_context_on_templatetags(self, request, instance):
        if self._context == 'get_all':
            return {}

        return {
            'transactions': instance.transactions.filter(user=request.user).order_by('-date', '-id'),
            'position': InvestmentService.get_position(instance),
            'default_wallet': InvestmentTransactionService.get_default_wallet(request.user),
        }

    @method_decorator(login_required)
    def apply_from_wallet(self, request, id):
        investment = self.service.get_by_id(id, request.user)
        wallet = InvestmentTransactionService.get_or_create_default_wallet(request.user)
        if investment.id == wallet.id:
            messages.warning(request, 'A carteira default não pode receber aplicação dela mesma.')
            return redirect('detail_investment', id=investment.id)

        if request.method == 'POST':
            form = InvestmentCashMovementForm(request.POST, investment=investment)
            if form.is_valid():
                InvestmentTransactionService.transfer_between_investments(
                    source=wallet,
                    destination=investment,
                    amount=form.cleaned_data['amount'],
                    date=form.cleaned_data['date'],
                    due_date=form.cleaned_data['due_date'],
                    quantity=form.cleaned_data.get('quantity'),
                    unit_price=form.cleaned_data.get('unit_price'),
                    notes=form.cleaned_data['notes'],
                )
                return redirect('investments_dashboard')
        else:
            form = InvestmentCashMovementForm(initial={'due_date': investment.due_date}, investment=investment)

        self._context = 'apply_from_wallet'
        return self._render(
            request,
            form,
            'investment/cash_movement_form.html',
            {
                'investment': investment,
                'movement_title': 'Aplicar do caixa',
                'movement_description': f'Origem: {wallet}. Destino: {investment}.',
            },
        )

    @method_decorator(login_required)
    def redeem_to_wallet(self, request, id):
        investment = self.service.get_by_id(id, request.user)
        wallet = InvestmentTransactionService.get_or_create_default_wallet(request.user)
        if investment.id == wallet.id:
            messages.warning(request, 'A carteira default não pode ser resgatada para ela mesma.')
            return redirect('detail_investment', id=investment.id)

        if request.method == 'POST':
            form = InvestmentRedemptionForm(request.POST, investment=investment)
            if form.is_valid():
                InvestmentTransactionService.redeem_to_wallet(
                    source=investment,
                    gross_amount=form.cleaned_data['amount'],
                    principal_amount=form.cleaned_data['principal_amount'],
                    date=form.cleaned_data['date'],
                    quantity=form.cleaned_data.get('quantity'),
                    unit_price=form.cleaned_data.get('unit_price'),
                    notes=form.cleaned_data['notes'],
                )
                return redirect('investments_dashboard')
        else:
            form = InvestmentRedemptionForm(investment=investment)

        self._context = 'redeem_to_wallet'
        return self._render(
            request,
            form,
            'investment/cash_movement_form.html',
            {
                'investment': investment,
                'movement_title': 'Resgatar para caixa',
                'movement_description': f'Origem: {investment}. Destino: {wallet}.',
            },
        )
