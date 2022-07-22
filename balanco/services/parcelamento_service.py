from balanco.models import Parcelamento


def cadastrar_parcelamento(parcelamento):
    novo_parcelamento = Parcelamento.objects.create(
        data_lancamento=parcelamento.data_lancamento,
        descricao=parcelamento.descricao,
        usuario=parcelamento.usuario
    )
    return novo_parcelamento


def listar_parcelamentos(usuario):
    return Parcelamento.objects.filter(usuario=usuario)


def listar_parcelamento_id(id, usuario):
    return Parcelamento.objects.filter(id=id, usuario=usuario).first()


def editar_parcelamento(parcelamento_antigo, parcelamento_novo):
    parcelamento_antigo.data_lancamento = parcelamento_novo.data_lancamento
    parcelamento_antigo.descricao = parcelamento_novo.descricao
    parcelamento_antigo.save(force_update=True)


def remover_parcelamento(parcelamento):
    parcelamento.delete()
