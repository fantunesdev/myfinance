from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator

from statement.forms.core.subcategory_chart_config import SubcategoryChartConfigForm
from statement.models import SubcategoryChartConfig
from statement.services.core.subcategory import SubcategoryChartConfigService
from statement.views.base_view import BaseView


class SubcategoryChartConfigView(BaseView):
    class_has_user = True
    class_title = 'Configuração de gráficos por subcategoria'
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
