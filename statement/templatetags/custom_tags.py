from django import template
from statement.services import portion_services
from django.utils.formats import number_format

register = template.Library()


@register.simple_tag
def get_cumulative_total_for_dream(dream_id, user):
    portions = portion_services.list_portions_by_dream(dream_id, user)
    total = sum(portion.value for portion in portions)
    formatted_total = number_format(total, decimal_pos=2, force_grouping=True)
    return f'R$ {formatted_total}'


@register.simple_tag
def get_remaining_value_for_dream(dream_id, dream_value, user):
    remaining_value = portion_services.calculate_remaining_value(dream_id, dream_value, user)
    formatted_total = number_format(remaining_value, decimal_pos=2, force_grouping=True)
    return f'R$ {formatted_total}'

@register.simple_tag
def calcule_remaining_installment_value(dream_id, dream_value, dream_installments, user):
    remaining_value = portion_services.calculate_remaining_value(dream_id, dream_value, user)
    remaining_installments = remaining_value / dream_installments
    formatted_total = number_format(remaining_installments, decimal_pos=2, force_grouping=True)
    return f'R$ {formatted_total}'
