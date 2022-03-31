from balanco.models import Categoria


def cadastrar_categoria(categoria):
    Categoria.objects.create(
        tipo=categoria.tipo,
        descricao=categoria.descricao,
        cor=categoria.cor,
        icone=categoria.icone,
        usuario=categoria.usuario
    )


def listar_categorias(usuario):
    return Categoria.objects.filter(usuario=usuario)


def listar_categorias_tipo(tipo, usuario):
    return Categoria.objects.filter(tipo=tipo, usuario=usuario)


def listar_categoria_id(id, usuario):
    categoria = Categoria.objects.get(id=id, usuario=usuario)
    return categoria


def editar_categoria(categoria_antiga, categoria_nova):
    categoria_antiga.tipo = categoria_nova.tipo
    categoria_antiga.descricao = categoria_nova.descricao
    categoria_antiga.cor = categoria_nova.cor
    categoria_antiga.icone = categoria_nova.icone
    categoria_antiga.usuario = categoria_nova.usuario
    categoria_antiga.save(force_update=True)


def remover_categoria(categoria):
    categoria.delete()
