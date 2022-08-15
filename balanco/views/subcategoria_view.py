from django.shortcuts import redirect, render

from balanco.views.movimentacao_view import templatetags
from balanco.entidades.subcategoria import Subcategoria
from balanco.forms import subcategoria_form, general_forms
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
    templatetags['subcategoria_antiga'] = None
    templatetags['form_subcategoria'] = form_subcategoria
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'subcategoria/form_subcategoria.html', templatetags)


def listar_subcategorias(request):
    templatetags['subcategorias'] = subcategoria_service.listar_subcategorias(request.user)
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'subcategoria/listar.html', templatetags)


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
    templatetags['subcategoria_antiga'] = subcategoria_antiga
    templatetags['form_subcategoria'] = form_subcategoria
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'subcategoria/editar.html', templatetags)


def remover_subcategoria(request, id):
    subcategoria = subcategoria_service.listar_subcategoria_id(id, request.user)
    form_exclusao = general_form.ExclusaoForm()
    if request.POST.get('confirmacao'):
        subcategoria_service.remover_subcategoria(subcategoria)
        return redirect('form_subcategoria')
    templatetags['subcategoria'] = subcategoria
    templatetags['form_exclusao'] = form_exclusao
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'subcategoria/confirma_exclusao.html', templatetags)
