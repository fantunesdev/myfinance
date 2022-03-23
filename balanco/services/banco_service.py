from ..models import Banco


def cadastrar_banco(banco):
    Banco.objects.create(
        descricao=banco.descricao,
        codigo=banco.codigo,
        icone=banco.icone
    )


def listar_bancos():
    return Banco.objects.all()


def listar_banco(id):
    return Banco.objects.get(id=id)


def editar_banco(banco_antigo, banco_novo):
    banco_antigo.descricao = banco_novo.descricao
    banco_antigo.codigo = banco_novo.codigo
    banco_antigo.icone = banco_novo.icone
    banco_antigo.save(force_update=True)


def remover_banco(banco):
    banco.delete()
