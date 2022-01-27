from ..models.movimentacao_model import Categoria


def cadastrar_categoria(categoria):
    Categoria.objects.create(
        tipo=categoria.tipo,
        descricao=categoria.descricao,
        cor=categoria.cor,
        icone=categoria.icone
    )


def listar_categorias():
    return Categoria.objects.all()


def listar_categorias_tipo(tipo):
    return Categoria.objects.filter(tipo=tipo)


def listar_categoria_id(id):
    categoria = Categoria.objects.get(id=id)
    return categoria


def editar_categoria(categoria_antiga, categoria_nova):
    categoria_antiga.tipo = categoria_nova.tipo
    categoria_antiga.descricao = categoria_nova.descricao
    categoria_antiga.cor = categoria_nova.cor
    categoria_antiga.icone = categoria_nova.icone
    categoria_antiga.save(force_update=True)


def remover_categoria(categoria):
    categoria.delete()
