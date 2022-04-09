from balanco.models import Parcelamento


def cadastrar_parcelamento(parcela):
    return Parcelamento.objects.create(usuario=parcela.usuario)


def listar_parcelamentos(usuario):
    return Parcelamento.objects.filter(usuario=usuario)


def listar_parcelamento_id(id, usuario):
    return Parcelamento.objects.filter(id=id, usuario=usuario).first()


def remover_parcelamentos(parcelamento):
    parcelamento.delete()
