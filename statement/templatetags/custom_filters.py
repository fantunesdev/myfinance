from django import template

register = template.Library()


@register.filter(name='to_currency')
def to_currency(float, symbol):
    return f'{symbol} {float:_.2f}'.replace('.', ',').replace('_', '.')


@register.filter(name='to_reais')
def to_reais(float):
    return f'R$ {float:_.2f}'.replace('.', ',').replace('_', '.')


@register.filter(name='total_amount')
def total_amount(transaction):
    total = 0
    for i in transaction:
        total += i.value
    return f'{transaction[0].currency.symbol} {total:_.2f}'.replace('.', ',').replace('_', '.')


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
