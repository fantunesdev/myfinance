from django import forms

from statement.forms.base_form import BaseForm
from statement.models import SubcategoryChartConfig
from statement.services.core.subcategory import SubcategoryService

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

CHART_LABELS = (
    'Receitas e despesas do mês',
    'Demonstrativo anual',
    'Despesas por categoria no mês',
    'Despesas por categoria no ano',
    'Evolução dos gastos no mês',
)

CHART_DESCRIPTIONS = (
    (
        'O gráfico de rosca compara quanto entrou e quanto saiu no mês selecionado. '
        'Ao ocultar uma subcategoria, seus valores deixam de compor essa comparação. '
        'Aqui, todas as saídas contam como despesas, inclusive investimentos.'
    ),
    (
        'O demonstrativo reúne a evolução mês a mês e o gráfico de rosca com receitas, despesas e investimentos '
        'do ano selecionado. Ao ocultar uma subcategoria, seus valores saem dos dois gráficos. '
        'As saídas de subcategorias de investimento ficam separadas das despesas.'
    ),
    (
        'As barras mostram quanto você gastou em cada categoria no mês selecionado. '
        'Ao ocultar uma subcategoria, seus gastos deixam de compor a barra da categoria correspondente. '
        'Use essa lista para escolher quais gastos entram na comparação mensal.'
    ),
    (
        'As barras comparam o total de gastos por categoria no ano selecionado. '
        'Ao ocultar uma subcategoria, seus gastos deixam de compor a barra da categoria correspondente. '
        'Essa lista é independente da configuração das barras mensais.'
    ),
    (
        'A linha mostra como os gastos se acumulam dia após dia no mês selecionado, '
        'ajudando a acompanhar o ritmo das despesas. Ao ocultar uma subcategoria, seus valores deixam '
        'de entrar nesse acumulado, nas visualizações Consolidado, Cartão e À vista.'
    ),
)


class ChartExclusionsForm(forms.Form):
    chart = forms.ChoiceField(
        choices=tuple(zip(SubcategoryService.chart_flag_names, CHART_LABELS)),
        widget=forms.HiddenInput,
    )
    hidden_subcategories = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, configs, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hidden_subcategories'].choices = [
            (str(config.subcategory_id), str(config.subcategory)) for config in configs
        ]


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
