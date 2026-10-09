from statement.forms.base_form import BaseForm
from statement.models import SubcategoryChartConfig


CHART_CONFIG_HELP_TEXTS = {
    'show_in_monthly_cashflow_donut': (
        'Controla se lançamentos desta subcategoria aparecem no gráfico mensal de Receitas / Despesas. '
        'Saídas aparecem como despesas, mesmo quando forem investimentos.'
    ),
    'show_in_annual_statement': (
        'Controla se lançamentos desta subcategoria aparecem no dashboard anual. '
        'Subcategorias marcadas como investimento aparecem na fatia Investimentos.'
    ),
    'show_in_monthly_expense_category_bar': (
        'Controla se lançamentos desta subcategoria aparecem no gráfico mensal de despesas por categoria.'
    ),
    'show_in_annual_expense_category_bar': (
        'Controla se lançamentos desta subcategoria aparecem no gráfico anual de despesas por categoria.'
    ),
    'show_in_monthly_expense_line': (
        'Controla se lançamentos desta subcategoria entram na linha acumulada de gastos ao longo do mês.'
    ),
}


class SubcategoryChartConfigForm(BaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subcategory'].disabled = True

    class Meta:
        model = SubcategoryChartConfig
        fields = [
            'subcategory',
            'show_in_monthly_cashflow_donut',
            'show_in_annual_statement',
            'show_in_monthly_expense_category_bar',
            'show_in_annual_expense_category_bar',
            'show_in_monthly_expense_line',
        ]
        labels = {
            'subcategory': 'Subcategoria',
            'show_in_monthly_cashflow_donut': 'Exibir no donut mensal',
            'show_in_annual_statement': 'Exibir no demonstrativo anual',
            'show_in_monthly_expense_category_bar': 'Exibir na barra mensal por categoria',
            'show_in_annual_expense_category_bar': 'Exibir na barra anual por categoria',
            'show_in_monthly_expense_line': 'Exibir na linha mensal de gastos',
        }
        help_texts = CHART_CONFIG_HELP_TEXTS
