from ..models import SubCategoria


def cadastrar_subcategoria(subcategoria):
    SubCategoria.objects.create(
        descricao=subcategoria.descricao,
        categoria=subcategoria.categoria
    )


def listar_subcategorias(usuario):
    return SubCategoria.objects.filter(usuario=usuario)


def listar_subcategoria_id(id, usuario):
    return SubCategoria.objects.filter(id=id, usuario=usuario).first()


def editar_subcategoria(subcategoria_antiga, subcategoria_nova):
    subcategoria_antiga.descricao = subcategoria_nova.descricao
    subcategoria_antiga.categoria = subcategoria_nova.categoria
    subcategoria_antiga.save(force_update=True)


def remover_subcategoria(subcategoria):
    subcategoria.delete(subcategoria)
