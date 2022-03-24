from ..models import Movimentacao


def cadastrar_movimentacao(movimentacao):
    Movimentacao.objects.create(
        valor=movimentacao.valor,
        data=movimentacao.data,
        repetir=movimentacao.repetir,
        parcelas=movimentacao.parcelas,
        descricao=movimentacao.descricao,
        categoria=movimentacao.categoria,
        conta=movimentacao.conta,
        fixa=movimentacao.fixa,
        moeda=movimentacao.moeda,
        observacao=movimentacao.observacao,
        lembrar=movimentacao.lembrar,
        tipo=movimentacao.tipo,
        efetivado=movimentacao.efetivado
    )


def listar_movimentacoes():
    return Movimentacao.objects.all()


def listar_movimentacao_id(id):
    return Movimentacao.objects.get(id=id)


def editar_movimentacao(movimentacao_antiga, movimentacao_nova):
    movimentacao_antiga.valor = movimentacao_nova.valor
    movimentacao_antiga.data = movimentacao_nova.data
    movimentacao_antiga.repetir = movimentacao_nova.repetir
    movimentacao_antiga.parcelas = movimentacao_nova.parcelas
    movimentacao_antiga.descricao = movimentacao_nova.descricao
    movimentacao_antiga.categoria = movimentacao_nova.categoria
    movimentacao_antiga.conta = movimentacao_nova.conta
    movimentacao_antiga.fixa = movimentacao_nova.fixa
    movimentacao_antiga.moeda = movimentacao_nova.moeda
    movimentacao_antiga.observacao = movimentacao_nova.observacao
    movimentacao_antiga.lembrar = movimentacao_nova.lembrar
    movimentacao_antiga.tipo = movimentacao_nova.tipo
    movimentacao_antiga.efetivado = movimentacao_nova.efetivado
    movimentacao_antiga.save(force_update=True)


def remover_movimentacao(movimentacao):
    movimentacao.delete()
