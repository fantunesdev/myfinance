from balanco.models import Categoria


def listar_categoria_tipo(tipo, usuario):
    return Categoria.objects.filter(tipo=tipo, usuario=usuario)
