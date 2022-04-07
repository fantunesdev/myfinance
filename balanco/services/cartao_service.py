from ..models import Cartao


def cadastrar_cartao(cartao):
    Cartao.objects.create(
        bandeira=cartao.bandeira,
        icone=cartao.icone,
        descricao=cartao.descricao,
        limite=cartao.limite,
        conta=cartao.conta,
        vencimento=cartao.vencimento,
        fechamento=cartao.fechamento,
        tela_inicial=cartao.tela_inicial,
        usuario=cartao.usuario
    )


def listar_cartoes(usuario):
    return Cartao.objects.filter(usuario=usuario)


def listar_cartao_id(id, usuario):
    return Cartao.objects.filter(id=id, usuario=usuario).first()


def editar_cartao(cartao_antigo, cartao_novo):
    cartao_antigo.bandeira = cartao_novo.bandeira
    cartao_antigo.icone = cartao_novo.icone
    cartao_antigo.descricao = cartao_novo.descricao
    cartao_antigo.limite = cartao_novo.limite
    cartao_antigo.conta = cartao_novo.conta
    cartao_antigo.vencimento = cartao_novo.vencimento
    cartao_antigo.fechamento = cartao_novo.fechamento
    cartao_antigo.tela_inicial = cartao_novo.tela_inicial
    cartao_antigo.usuario = cartao_novo.usuario
    cartao_antigo.save(force_update=True)


def remover_cartao(cartao):
    cartao.delete()
