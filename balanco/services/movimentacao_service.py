from ..models import Movimentacao


def cadastrar_movimentacao(movimentacao):
    Movimentacao.objects.create(
        data=movimentacao.data,
        pagamento=movimentacao.pagamento,
        conta=movimentacao.conta,
        cartao=movimentacao.cartao,
        categoria=movimentacao.categoria,
        subcategoria=movimentacao.subcategoria,
        descricao=movimentacao.descricao,
        valor=movimentacao.valor,
        parcelas=movimentacao.parcelas,
        pagas=movimentacao.pagas,
        fixa=movimentacao.fixa,
        anual=movimentacao.anual,
        moeda=movimentacao.moeda,
        observacao=movimentacao.observacao,
        lembrar=movimentacao.lembrar,
        tipo=movimentacao.tipo,
        efetivado=movimentacao.efetivado,
        tela_inicial=movimentacao.tela_inicial,
        usuario=movimentacao.usuario
    )


def listar_movimentacoes(usuario):
    return Movimentacao.objects.filter(usuario=usuario)


def listar_movimentacoes_ano_mes(ano, mes, usuario):
    return Movimentacao.objects.filter(pagamento__year=ano, pagamento__month=mes, usuario=usuario).order_by('data')


def listar_anos_meses(usuario):
    anos_meses = Movimentacao.objects.filter(usuario=usuario).dates(field_name='pagamento', kind='month', order='DESC')[:12]
    return reversed(anos_meses)


def listar_movimentacoes_conta_id(id, usuario):
    return Movimentacao.objects.filter(conta=id, usuario=usuario)


def listar_movimentacao_id(id, usuario):
    return Movimentacao.objects.get(id=id, usuario=usuario)


def editar_movimentacao(movimentacao_antiga, movimentacao_nova):
    movimentacao_antiga.data = movimentacao_nova.data
    movimentacao_antiga.pagamento = movimentacao_nova.pagamento
    movimentacao_antiga.conta = movimentacao_nova.conta
    movimentacao_antiga.cartao = movimentacao_nova.cartao
    movimentacao_antiga.categoria = movimentacao_nova.categoria
    movimentacao_antiga.subcategoria = movimentacao_nova.subcategoria
    movimentacao_antiga.descricao = movimentacao_nova.descricao
    movimentacao_antiga.valor = movimentacao_nova.valor
    movimentacao_antiga.parcelas = movimentacao_nova.parcelas
    movimentacao_antiga.pagas = movimentacao_nova.pagas
    movimentacao_antiga.fixa = movimentacao_nova.fixa
    movimentacao_antiga.anual = movimentacao_nova.anual
    movimentacao_antiga.moeda = movimentacao_nova.moeda
    movimentacao_antiga.observacao = movimentacao_nova.observacao
    movimentacao_antiga.lembrar = movimentacao_nova.lembrar
    movimentacao_antiga.tipo = movimentacao_nova.tipo
    movimentacao_antiga.efetivado = movimentacao_nova.efetivado
    movimentacao_antiga.tela_inicial = movimentacao_nova.tela_inicial
    movimentacao_antiga.usuario = movimentacao_nova.usuario
    movimentacao_antiga.save(force_update=True)


def remover_movimentacao(movimentacao):
    movimentacao.delete()
