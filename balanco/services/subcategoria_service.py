from ..models import Subcategoria


def cadastrar_subcategoria(subcategoria):
    Subcategoria.objects.create(
        descricao=subcategoria.descricao,
        categoria=subcategoria.categoria,
        usuario=subcategoria.usuario,
    )


def listar_subcategorias(usuario):
    return Subcategoria.objects.filter(usuario=usuario)


def listar_subcategoria_id(id, usuario):
    return Subcategoria.objects.filter(id=id, usuario=usuario).first()


def editar_subcategoria(subcategoria_antiga, subcategoria_nova):
    subcategoria_antiga.descricao = subcategoria_nova.descricao
    subcategoria_antiga.categoria = subcategoria_nova.categoria
    subcategoria_antiga.save(force_update=True)


def remover_subcategoria(subcategoria):
    subcategoria.delete(subcategoria)
