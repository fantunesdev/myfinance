from django import template

register = template.Library()


@register.filter(name='converter_reais')
def converter_reais(float, simbolo):
    return f'{simbolo} {float:_.2f}'.replace('.', ',').replace('_', '.')
