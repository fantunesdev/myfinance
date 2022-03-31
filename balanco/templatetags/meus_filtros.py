from django import template

register = template.Library()


@register.filter(name='formatar_moeda')
def formatar_moeda(float, simbolo):
    return f'{simbolo} {float:_.2f}'.replace('.', ',').replace('_', '.')


@register.filter(name='formatar_reais')
def formatar_reais(float):
    return f'R$ {float:_.2f}'.replace('.', ',').replace('_', '.')
