from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator

from statement.forms.core.subcategory_chart_config import (
    CHART_DESCRIPTIONS,
    CHART_LABELS,
    ChartExclusionsForm,
    SubcategoryChartConfigForm,
)
from statement.models import SubcategoryChartConfig
from statement.services.core.subcategory import SubcategoryChartConfigService, SubcategoryService
from statement.views.base_view import BaseView


class SubcategoryChartConfigView(BaseView):
    class_has_user = True
    class_title = 'Visibilidade nos gráficos'
    column_names = [
        'Subcategoria',
        'Donut mensal',
        'Demonstrativo anual',
        'Barra mensal',
        'Barra anual',
        'Linha mensal',
    ]
    class_form = SubcategoryChartConfigForm
    list_fields = [
        'subcategory',
        'show_in_monthly_cashflow_donut',
        'show_in_annual_statement',
        'show_in_monthly_expense_category_bar',
        'show_in_annual_expense_category_bar',
        'show_in_monthly_expense_line',
    ]
    model = SubcategoryChartConfig
    service = SubcategoryChartConfigService
    redirect_url = 'get_all_subcategory_chart_config'
    actions_list = {
        'create': False,
        'delete': False,
        'detail': False,
        'get_all': True,
        'update': True,
    }
    template_is_global = {
        'create': True,
        'delete': True,
        'detail': True,
        'get_all': True,
        'update': True,
    }
    show_duplicate_checker = False
    chart_locations = (
        ('monthly-cashflow.svg', 'Início → mês → Dashboard → Receitas / Despesas'),
        ('annual-statement.svg', 'Dashboards → Demonstrativo → linhas e Receitas / Despesas / Investimentos'),
        ('monthly-categories.svg', 'Início → mês → Dashboard → despesas por categoria'),
        ('annual-categories.svg', 'Dashboards → Demonstrativo → ícone de barras (Gastos por categoria)'),
        ('monthly-line.svg', 'Início → mês → Dashboard → ícone de linha (Gastos ao longo do mês)'),
    )

    @method_decorator(login_required)
    def get_all(self, request):
        self._context = 'get_all'
        configs = list(self.service.get_all(request.user))
        submitted = ChartExclusionsForm(request.POST, configs=configs) if request.method == 'POST' else None
        if submitted is not None and submitted.is_valid():
            field = submitted.cleaned_data['chart']
            hidden_ids = submitted.cleaned_data['hidden_subcategories']
            # Update only the selected chart and the authenticated user's preferences.
            with transaction.atomic():
                own_configs = self.model.objects.filter(user=request.user)
                own_configs.filter(subcategory_id__in=hidden_ids).update(**{field: False})
                own_configs.exclude(subcategory_id__in=hidden_ids).update(**{field: True})
            messages.success(request, 'Preferências do gráfico salvas.')
            return redirect(f'{reverse(self.redirect_url)}?grafico={field}#chart-{field}')

        charts = []
        for field, label, description, (preview, location) in zip(
            SubcategoryService.chart_flag_names,
            CHART_LABELS,
            CHART_DESCRIPTIONS,
            self.chart_locations,
        ):
            hidden = [config for config in configs if not getattr(config, field)]
            bound = submitted is not None and request.POST.get('chart') == field
            form = (
                submitted
                if bound
                else ChartExclusionsForm(
                    configs=configs,
                    initial={'chart': field, 'hidden_subcategories': [str(c.subcategory_id) for c in hidden]},
                    auto_id=False,
                )
            )
            selected = set(form['hidden_subcategories'].value() or [])
            charts.append(
                {
                    'field': field,
                    'label': label,
                    'help': description,
                    'hidden': hidden,
                    'visible_count': len(configs) - len(hidden),
                    'form': form,
                    'selected': [config for config in configs if str(config.subcategory_id) in selected],
                    'preview': f'img/chart-previews/{preview}',
                    'location': location,
                    'open': bound or request.GET.get('grafico') == field,
                }
            )
        return self._render(
            request,
            None,
            'subcategory_chart_config/list.html',
            {
                'charts': charts,
                'total': len(configs),
                'options': configs,
                'invalid_form': submitted if submitted is not None and 'chart' in submitted.errors else None,
            },
        )

    @method_decorator(login_required)
    def update(self, request, id):
        instance = self.service.get_by_id(id, request.user)
        if request.method == 'POST':
            form = self.class_form(request.POST, instance=instance)
            if form.is_valid():
                self.service.update(form, instance)
                return redirect(self.redirect_url)
        else:
            form = self.class_form(instance=instance)

        return self._render(
            request,
            form,
            'base/form.html',
            {
                'old_instance': instance,
                'update': True,
            },
        )
