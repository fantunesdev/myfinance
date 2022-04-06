from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from balanco.views.movimentacao_view import template_tags
from ..services import categoria_service, conta_service
from ..forms.categoria_form import CategoriaForm
from ..forms.general_form import ExclusaoForm
from ..entidades.categoria import Categoria


@login_required
def cadastrar_categoria(request):
    if request.method == 'POST':
        form_categoria = CategoriaForm(request.POST, request.FILES)
        if form_categoria.is_valid():
            categoria_nova = Categoria(tipo=form_categoria.cleaned_data['tipo'],
                                       descricao=form_categoria.cleaned_data['descricao'],
                                       cor=form_categoria.cleaned_data['cor'],
                                       icone=form_categoria.cleaned_data['icone'],
                                       usuario=request.user)
            categoria_service.cadastrar_categoria(categoria_nova)
            return redirect('configurar')
    else:
        form_categoria = CategoriaForm()
    template_tags['contas'] = conta_service.listar_contas(request.user)
    template_tags['form_categoria'] = form_categoria
    if 'categoria_antiga' in template_tags.keys():
        template_tags.pop('categoria_antiga')
    return render(request, 'categoria/form_categoria.html', template_tags)


@login_required
def listar_categorias(request):
    template_tags['categorias'] = categoria_service.listar_categorias(request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'categoria/listar.html', template_tags)


@login_required
def listar_categorias_tipo(request, tipo):
    template_tags['categorias'] = categoria_service.listar_categorias_tipo(tipo, request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    template_tags['contas'] = tipo
    return render(request, 'categoria/listar_tipo.html', template_tags)


@login_required
def listar_categoria_id(request, id):
    template_tags['categoria'] = categoria_service.listar_categoria_id(id, request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'categorias/listar_id.html', template_tags)


@login_required
def editar_categoria(request, id):
    categoria_antiga = categoria_service.listar_categoria_id(id, request.user)
    form_categoria = CategoriaForm(request.POST or None, request.FILES or None, instance=categoria_antiga)
    if form_categoria.is_valid():
        categoria_nova = Categoria(tipo=form_categoria.cleaned_data['tipo'],
                                   descricao=form_categoria.cleaned_data['descricao'],
                                   cor=form_categoria.cleaned_data['cor'],
                                   icone=form_categoria.cleaned_data['icone'],
                                   usuario=request.user)
        categoria_service.editar_categoria(categoria_antiga, categoria_nova)

        return redirect('configurar')
    template_tags['form_categoria'] = form_categoria
    template_tags['categoria_antiga'] = categoria_antiga
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'categoria/editar.html', template_tags)


@login_required
def remover_categoria(request, id):
    categoria = categoria_service.listar_categoria_id(id, request.user)
    if request.method == 'POST':
        categoria_service.remover_categoria(categoria)
        return redirect('configurar')
    template_tags['contas'] = conta_service.listar_contas(request.user)
    template_tags['categoria'] = categoria
    template_tags['form_exclusao'] = ExclusaoForm()
    return render(request, 'categoria/confirma_exclusao.html', template_tags)
