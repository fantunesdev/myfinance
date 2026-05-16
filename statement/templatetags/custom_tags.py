from datetime import date

from dateutil.relativedelta import relativedelta
from django import template
from django.utils.formats import number_format

from statement.models import Dream

register = template.Library()


def _calculate_remaining_installment_value(dream):
    """Calcula o valor da parcela mensal necessária para atingir o objetivo."""
    today = date.today()
    if dream.limit_date and dream.limit_date > today:
        diference_months_in_years = (dream.limit_date.year - today.year) * 12
        difference_months = dream.limit_date.month - today.month
        remaining_months = diference_months_in_years + difference_months
        if remaining_months == 0:
            remaining_months = 1
    else:
        remaining_months = 1

    return dream.remaining_value / remaining_months


@register.simple_tag
def get_cumulative_total_for_dream(dream_id, user):
    """Retorna o valor acumulado de contribuições para um sonho via Transactions."""
    try:
        dream = Dream.objects.get(id=dream_id, user=user)
        current_value = dream.current_value
        formatted_total = number_format(current_value, decimal_pos=2, force_grouping=True)
        return f'R$ {formatted_total}'
    except Dream.DoesNotExist:
        return 'R$ 0,00'


@register.simple_tag
def get_remaining_value_for_dream(dream_id, dream_value, user):
    """Retorna o valor faltante para atingir o objetivo do sonho."""
    try:
        dream = Dream.objects.get(id=dream_id, user=user)
        remaining_value = dream.remaining_value
        formatted_total = number_format(remaining_value, decimal_pos=2, force_grouping=True)
        return f'R$ {formatted_total}'
    except Dream.DoesNotExist:
        return f'R$ {number_format(dream_value, decimal_pos=2, force_grouping=True)}'


@register.simple_tag
def calcule_remaining_installment_value(dream_id, dream_value, dream_limit_date, user):
    """Calcula o valor da parcela mensal necessária para atingir o objetivo."""
    try:
        dream = Dream.objects.get(id=dream_id, user=user)
        remaining_limit_date = _calculate_remaining_installment_value(dream)
    except Dream.DoesNotExist:
        dream = Dream(target_value=dream_value, limit_date=dream_limit_date)
        remaining_limit_date = _calculate_remaining_installment_value(dream)

    formatted_total = number_format(remaining_limit_date, decimal_pos=2, force_grouping=True)
    return f'R$ {formatted_total}'


@register.simple_tag
def total_remaining_installment_value_for_dreams(dreams):
    """Calcula o total das parcelas mensais dos sonhos listados."""
    total = sum(_calculate_remaining_installment_value(dream) for dream in dreams)
    formatted_total = number_format(total, decimal_pos=2, force_grouping=True)
    return f'R$ {formatted_total}'


@register.simple_tag
def calculate_remaining_months(dream):
    """Calcula os meses restantes até a data limite do sonho."""
    today = date.today()
    if dream.limit_date and dream.limit_date > today:
        diference_months_in_years = (dream.limit_date.year - today.year) * 12
        difference_months = dream.limit_date.month - today.month
        return diference_months_in_years + difference_months
    return 0


@register.filter
def capitalize_first(value):
    """
    Capitaliza apenas a primeira letra de cada palavra.
    """
    if isinstance(value, str):
        return value.capitalize()  # Primeira letra maiúscula, as outras minúsculas
    return value
