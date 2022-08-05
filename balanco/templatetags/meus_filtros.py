from django import template

register = template.Library()


@register.filter(name='formatar_moeda')
def formatar_moeda(float, simbolo):
    return f'{simbolo} {float:_.2f}'.replace('.', ',').replace('_', '.')


@register.filter(name='formatar_reais')
def formatar_reais(float):
    return f'R$ {float:_.2f}'.replace('.', ',').replace('_', '.')


@register.filter(name='valor_total')
def valor_total(movimentacoes):
    total = 0
    for i in movimentacoes:
        total += i.valor
    return f'{movimentacoes[0].moeda.simbolo} {total:_.2f}'


@register.filter(name='descricao_parcelas')
def descricao_parcelas(movimentacao):
    if movimentacao.numero_parcelas == 0:
        return movimentacao.descricao
    else:
        return f'{movimentacao.descricao} ({movimentacao.pagas}/{movimentacao.numero_parcelas})'


@register.filter(name='bool_portuguese')
def bool_portuguese(boolean):
    print(boolean)
    if boolean:
        return 'Sim'
    return 'Não'
