from balanco.forms.movimentacao_form import MovimentacaoEntradaForm


def validar_tipo(tipo):
    if tipo == 'entrada':
        tipo = 0
    else:
        tipo = 1
    return tipo


def criar_formulario(tipo):
    if tipo == 'entrada':
        form = lambda *args: MovimentacaoEntradaForm()