from balanco.models import Bandeira


def cadastrar_bandeira(bandeira):
    Bandeira.objects.create(
        descricao=bandeira.descricao,
        icone=bandeira.icone
    )

def listar_bandeiras():
    return Bandeira.objects.all()


def listar_bandeira_id(id):
    return Bandeira.objects.get(id=id)


def editar_bandeira(bandeira_antiga, bandeira_nova):
    bandeira_antiga.descricao = bandeira_nova.descricao
    bandeira_antiga.icone = bandeira_nova.icone
    bandeira_antiga.save(force_update=True)


def remover_bandeira(bandeira):
    bandeira.delete()
