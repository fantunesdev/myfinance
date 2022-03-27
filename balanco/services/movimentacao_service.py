from ..models import Movimentacao


def cadastrar_movimentacao(movimentacao):
    Movimentacao.objects.create(
        data=movimentacao.data,
        conta=movimentacao.conta,
        categoria=movimentacao.categoria,
        descricao=movimentacao.descricao,
        valor=movimentacao.valor,
        parcelas=movimentacao.parcelas,
        pagas=movimentacao.pagas,
        fixa=movimentacao.fixa,
        moeda=movimentacao.moeda,
        observacao=movimentacao.observacao,
        lembrar=movimentacao.lembrar,
        tipo=movimentacao.tipo,
        efetivado=movimentacao.efetivado,
        tela_inicial=movimentacao.tela_inicial
    )


def listar_movimentacoes():
    return Movimentacao.objects.all()


def listar_movimentacoes_conta_id(id):
    return Movimentacao.objects.filter(conta=id)


def listar_movimentacao_id(id):
    return Movimentacao.objects.get(id=id)


def editar_movimentacao(movimentacao_antiga, movimentacao_nova):
    movimentacao_antiga.data = movimentacao_nova.data
    movimentacao_antiga.conta = movimentacao_nova.conta
    movimentacao_antiga.categoria = movimentacao_nova.categoria
    movimentacao_antiga.descricao = movimentacao_nova.descricao
    movimentacao_antiga.valor = movimentacao_nova.valor
    movimentacao_antiga.parcelas = movimentacao_nova.parcelas
    movimentacao_antiga.pagas = movimentacao_nova.pagas
    movimentacao_antiga.fixa = movimentacao_nova.fixa
    movimentacao_antiga.moeda = movimentacao_nova.moeda
    movimentacao_antiga.observacao = movimentacao_nova.observacao
    movimentacao_antiga.lembrar = movimentacao_nova.lembrar
    movimentacao_antiga.tipo = movimentacao_nova.tipo
    movimentacao_antiga.efetivado = movimentacao_nova.efetivado
    movimentacao_antiga.tela_inicial = movimentacao_nova.tela_inicial
    movimentacao_antiga.save(force_update=True)


def remover_movimentacao(movimentacao):
    movimentacao.delete()
