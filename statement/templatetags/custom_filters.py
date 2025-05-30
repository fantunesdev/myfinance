from django import template

register = template.Library()


@register.filter(name='to_currency')
def to_currency(float, symbol):
    return f'{symbol} {float:_.2f}'.replace('.', ',').replace('_', '.')


@register.filter(name='to_reais')
def to_reais(float):
    return f'R$ {float:_.2f}'.replace('.', ',').replace('_', '.')


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
    return f'{transactions[0].currency.symbol} {total:_.2f}'.replace('.', ',').replace('_', '.')


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
    return [(field.name, getattr(instance, field.name)) for field in instance._meta.fields]
