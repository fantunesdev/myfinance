from django.shortcuts import redirect, render

from balanco.views.movimentacao_view import template_tags
from balanco.entidades.subcategoria import Subcategoria
from balanco.forms import subcategoria_form, general_form
from balanco.services import subcategoria_service, conta_service


def cadastrar_subcategoria(request):
    if request.method == 'POST':
        form_subcategoria = subcategoria_form.SubcategoriaForm(request.POST)
        if form_subcategoria.is_valid():
            subcategoria = Subcategoria(
                descricao=form_subcategoria.cleaned_data['descricao'],
                categoria=form_subcategoria.cleaned_data['categoria'],
                usuario=request.user
            )
            subcategoria_service.cadastrar_subcategoria(subcategoria)
            return redirect('listar_mes_atual')
    else:
        form_subcategoria = subcategoria_form.SubcategoriaForm()
    template_tags['subcategoria_antiga'] = None
    template_tags['form_subcategoria'] = form_subcategoria
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'subcategoria/form_subcategoria.html', template_tags)


def listar_subcategorias(request):
    template_tags['subcategorias'] = subcategoria_service.listar_subcategorias(request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'subcategoria/listar.html', template_tags)


def editar_subcategoria(request, id):
    subcategoria_antiga = subcategoria_service.listar_subcategoria_id(id, request.user)
    form_subcategoria = subcategoria_form.SubcategoriaForm(request.POST or None, instance=subcategoria_antiga)
    if form_subcategoria.is_valid():
        subcategoria_nova = Subcategoria(
            descricao=form_subcategoria.cleaned_data['descricao'],
            categoria=form_subcategoria.cleaned_data['categoria'],
            usuario=request.user
        )
        subcategoria_service.editar_subcategoria(subcategoria_antiga, subcategoria_nova)
        return redirect('listar_mes_atual')
    template_tags['subcategoria_antiga'] = subcategoria_antiga
    template_tags['form_subcategoria'] = form_subcategoria
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'subcategoria/editar.html', template_tags)


def remover_subcategoria(request, id):
    subcategoria = subcategoria_service.listar_subcategoria_id(id, request.user)
    form_exclusao = general_form.ExclusaoForm()
    if request.POST.get('confirmacao'):
        subcategoria_service.remover_subcategoria(subcategoria)
        return redirect('form_subcategoria')
    template_tags['subcategoria'] = subcategoria
    template_tags['form_exclusao'] = form_exclusao
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'subcategoria/confirma_exclusao.html', template_tags)
