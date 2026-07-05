from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter(name='to_currency')
def to_currency(value, symbol):
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = 0.0
    return f'{symbol} {v:_.2f}'.replace('.', ',').replace('_', '.')


@register.filter(name='to_reais')
def to_reais(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = 0.0
    return f'R$ {v:_.2f}'.replace('.', ',').replace('_', '.')


@register.filter(name='format_quantity')
def format_quantity(value):
    if value in [None, '']:
        return ''

    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value

    if quantity == quantity.to_integral_value():
        return str(quantity.quantize(Decimal('1')))

    return format(quantity.normalize(), 'f').rstrip('0').rstrip('.').replace('.', ',')


@register.filter(name='handle_boolean')
def handle_boolean(value):
    return 'Sim' if value else 'Não'


@register.filter(name='handle_none')
def handle_none(value):
    return value if value else ''


@register.filter(name='handle_image')
def handle_image(value):
    return value.url if value else ''


@register.filter(name='total_amount')
def total_amount(transactions):
    """
    Retorna o valor total de uma lista de lançamentos.

    :transactions (list): Lista de lançamentos
    """
    total = 0
    for transaction in transactions:
        total += transaction.value
    try:
        t = float(total)
    except (TypeError, ValueError):
        t = 0.0
    return f'{transactions[0].currency.symbol} {t:_.2f}'.replace('.', ',').replace('_', '.')


@register.filter(name='paid_installments')
def paid_installments(transaction):
    if transaction.installments_number == 0:
        return transaction.description
    else:
        return f'{transaction.description} ({transaction.paid}/{transaction.installments_number})'


@register.filter(name='bool_to_portuguese')
def bool_to_portuguese(boolean):
    if boolean:
        return 'Sim'
    return 'Não'


@register.filter
def get_fields(instance):
    """Retorna uma lista de tuplas (campo, valor) da instância do modelo."""
    fields = [(field.name, getattr(instance, field.name)) for field in instance._meta.fields]
    field_names = {field[0] for field in fields}
    properties = [
        (name, getattr(instance, name))
        for name, attr in vars(type(instance)).items()
        if isinstance(attr, property)
    ]
    property_names = {field[0] for field in properties}
    annotations = [
        (name, value)
        for name, value in instance.__dict__.items()
        if name not in field_names and name not in property_names and not name.startswith('_')
    ]
    return fields + properties + annotations


@register.filter
def get_field_value(instance, field_name):
    """Retorna o valor de um campo, property ou annotation da instância."""
    return getattr(instance, field_name, '')
