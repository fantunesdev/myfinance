from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator

from investments.forms.investment import InvestmentApplicationFromWalletForm
from investments.forms.transaction import InvestmentTransactionForm
from investments.models import InvestmentTransaction
from investments.services.transaction import InvestmentTransactionService
from investments.views.base import InvestmentCrudView


class InvestmentTransactionView(InvestmentCrudView):
    class_title = 'Movimentações'
    class_form = InvestmentTransactionForm
    model = InvestmentTransaction
    service = InvestmentTransactionService
    redirect_url = reverse_lazy('investments_dashboard')
    column_names = ['Data', 'Investimento', 'Tipo', 'Valor']
    list_fields = ['date', 'investment', 'type_label', 'amount']

    @method_decorator(login_required)
    def apply_from_wallet_transaction(self, request, id):
        wallet_transaction = self.service.get_by_id(id, request.user)
        wallet = InvestmentTransactionService.get_or_create_default_wallet(request.user)

        if wallet_transaction.investment_id != wallet.id or wallet_transaction.type != 'aporte':
            messages.warning(request, 'Só é possível aplicar a partir de um aporte no caixa de investimentos.')
            return redirect('detail_investment', id=wallet.id)

        initial = {
            'date': wallet_transaction.date,
            'amount': wallet_transaction.amount,
            'notes': wallet_transaction.notes,
        }

        if request.method == 'POST':
            form = InvestmentApplicationFromWalletForm(request.POST, user=request.user, wallet=wallet)
            if form.is_valid():
                InvestmentTransactionService.transfer_between_investments(
                    source=wallet,
                    destination=form.cleaned_data['investment'],
                    amount=form.cleaned_data['amount'],
                    date=form.cleaned_data['date'],
                    notes=form.cleaned_data['notes'],
                )
                return redirect('investments_dashboard')
        else:
            form = InvestmentApplicationFromWalletForm(initial=initial, user=request.user, wallet=wallet)

        self._context = 'apply_from_wallet_transaction'
        return self._render(
            request,
            form,
            'investment/cash_movement_form.html',
            {
                'investment': wallet,
                'movement_title': 'Aplicar a partir do caixa',
                'movement_description': f'Origem: {wallet_transaction}. Escolha o investimento de destino.',
            },
        )
