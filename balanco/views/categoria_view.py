from django.shortcuts import redirect, render
from ..services import categoria_service
from ..forms.categoria_form import CategoriaForm
from ..entidades.categoria import Categoria


def cadastrar_categoria(request):
    if request.method == 'POST':
        form_categoria = CategoriaForm(request.POST, request.FILES)
        if form_categoria.is_valid():
            categoria_nova = Categoria(tipo=form_categoria.cleaned_data['tipo'],
                                       descricao=form_categoria.cleaned_data['descricao'],
                                       cor=form_categoria.cleaned_data['cor'],
                                       icone=form_categoria.cleaned_data['icone'])
            categoria_service.cadastrar_categoria(categoria_nova)
            return redirect('listar_categorias')
    else:
        form_categoria = CategoriaForm()
    return render(request, 'categoria/cadastrar.html',
                  {'form_categoria': form_categoria})


def listar_categorias(request):
    categorias = categoria_service.listar_categorias()
    return render(request, 'categoria/listar.html', {'categorias': categorias})


def listar_categorias_tipo(request, tipo):
    categorias = categoria_service.listar_categorias_tipo(tipo)
    return render(request, 'categoria/listar_tipo.html', {'categorias': categorias,
                                                          'tipo': tipo})


def listar_categoria_id(request, id):
    categoria = categoria_service.listar_categoria_id(id)
    return render(request, 'categorias/listar_id.html', {'categoria': categoria})


def editar_categoria(request, id):
    categoria_antiga = categoria_service.listar_categoria_id(id)
    form_categoria = CategoriaForm(request.POST or None, request.FILES or None, instance=categoria_antiga)
    if form_categoria.is_valid():
        categoria_nova = Categoria(tipo=form_categoria.cleaned_data['tipo'],
                                   descricao=form_categoria.cleaned_data['descricao'],
                                   cor=form_categoria.cleaned_data['cor'],
                                   icone=form_categoria.cleaned_data['icone'])
        categoria_service.editar_categoria(categoria_antiga, categoria_nova)

        return redirect('listar_categorias')
    return render(request, 'categoria/editar.html', {'form_categoria': form_categoria,
                                                     'categoria_antiga': categoria_antiga})


def remover_categoria(request, id):
    categoria = categoria_service.listar_categoria_id(id)
    if request.method == 'POST':
        categoria_service.remover_categoria(categoria)
        return redirect('listar_categorias')
    return render(request, 'categoria/confirma_exclusao.html', {'categoria': categoria})
