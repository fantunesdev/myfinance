from balanco.models import Subcategoria


def listar_subcategoria_categoria(categoria_id, usuario):
    return Subcategoria.objects.select_related('categoria').filter(categoria=categoria_id, usuario=usuario)
