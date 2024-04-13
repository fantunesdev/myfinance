import datetime

from dateutil.relativedelta import relativedelta
from django import template
from django.utils.formats import number_format

from statement.services import dream_services
from statement.services import portion_services

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
def calcule_remaining_installment_value(dream_id, dream_value, dream_limit_date, user):
    remaining_value = portion_services.calculate_remaining_value(dream_id, dream_value, user)
    today = datetime.datetime.today()
    remaining_months = relativedelta(dream_limit_date - today).months
    remaining_limit_date = remaining_value / remaining_months
    formatted_total = number_format(remaining_limit_date, decimal_pos=2, force_grouping=True)
    return f'R$ {formatted_total}'


@register.simple_tag
def calculate_remaining_months(dream):
    today = datetime.datetime.today()
    return dream.limit_date.month - today.month
