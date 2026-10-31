from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator

from investments.services.investment import InvestmentService
from investments.services.transaction import InvestmentTransactionService
from statement.views.base_view import BaseView


class InvestmentsDashboardView(BaseView):
    class_title = 'Investimentos'

    @method_decorator(login_required)
    def dashboard(self, request):
        context = InvestmentService.get_dashboard(request.user)
        context['available_to_invest'] = sum(
            (position['value'] for position in context['positions'] if position['asset_type'] == 'currency'),
            Decimal('0'),
        )
        asset_types = {'fixed_income': 'Renda fixa', 'variable_income': 'Renda variável'}
        selected_type = request.GET.get('asset_type', '')
        if selected_type not in asset_types:
            selected_type = ''
        context['selected_asset_type'] = selected_type
        context['selected_asset_type_label'] = asset_types.get(selected_type, '')
        context['allocation_chart_data'] = {
            'selected_type': selected_type,
            'positions': [
                {
                    'label': str(position['investment']),
                    'asset_type': position['asset_type'],
                    'value': position['value'],
                    'url': reverse('detail_investment', args=[position['investment'].pk]),
                }
                for position in context['positions']
                if position['asset_type'] in asset_types and position['value'] > 0
            ],
        }
        if selected_type:
            context['positions'] = [position for position in context['positions'] if position['asset_type'] == selected_type]
        overview_query = request.GET.copy()
        overview_query.pop('asset_type', None)
        context['allocation_overview_url'] = f'?{overview_query.urlencode()}'
        context['show_all_brokers'] = request.GET.get('brokers') == 'all'
        if not context['show_all_brokers']:
            context['by_broker'] = [(broker, amount) for broker, amount in context['by_broker'] if amount > 0]
        context['show_all_positions'] = request.GET.get('positions') == 'all'
        if not context['show_all_positions']:
            context['positions'] = [position for position in context['positions'] if position['value'] > 0]
        for parameter, flag, anchor in (
            ('positions', 'show_all_positions', 'investment-positions'),
            ('brokers', 'show_all_brokers', 'investment-brokers'),
        ):
            query = request.GET.copy()
            if context[flag]:
                query.pop(parameter, None)
            else:
                query[parameter] = 'all'
            context[f'{parameter}_toggle_url'] = f'?{query.urlencode()}#{anchor}'
        context['default_wallet'] = InvestmentTransactionService.get_default_wallet(request.user)
        return self._render(request, None, 'investments/dashboard.html', context)

    @method_decorator(login_required)
    def create_default_wallet(self, request):
        if request.method == 'POST':
            try:
                InvestmentTransactionService.get_or_create_default_wallet(request.user)
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
            else:
                messages.success(request, 'Carteira padrão criada com sucesso.')
        return redirect('investments_dashboard')
