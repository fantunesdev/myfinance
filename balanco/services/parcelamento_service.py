from django.utils.datetime_safe import date

from balanco.models import Parcelamento


def cadastrar_parcelamento(parcelamento):
    novo_parcelamento = Parcelamento.objects.create(
        data_lancamento=parcelamento.data_lancamento,
        usuario=parcelamento.usuario
    )
    return novo_parcelamento


def listar_parcelamentos(usuario):
    return Parcelamento.objects.filter(usuario=usuario)


def listar_parcelamento_id(id, usuario):
    return Parcelamento.objects.filter(id=id, usuario=usuario).first()


def remover_parcelamento(parcelamento):
    parcelamento.delete()
