from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..forms.category_form import CategoryForm
from ..forms.general_forms import ExclusionForm
from ..repositories.templatetags_repository import set_menu_templatetags, set_templatetags
from ..services.category_service import CategoryService


@login_required
def create_category(request):
    """
    Cria uma nova categoria.

    Parâmetros:
        request (HttpRequest): Requisição HTTP contendo os dados da categoria.

    Retorna:
        HttpResponseRedirect: Redireciona para 'setup_settings' se a categoria for criada com sucesso.
        HttpResponse: Renderiza o formulário de criação de categoria caso os dados sejam inválidos ou a requisição seja GET.
    """
    if request.method == 'POST':
        category_form = CategoryForm(request.POST, request.FILES)
        if category_form.is_valid():
            CategoryService.create(category_form)
            return redirect('setup_settings')
    else:
        category_form = CategoryForm()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['category_form'] = category_form
    return render(request, 'category/category_form.html', templatetags)


@login_required
def update_category(request, id):
    """
    Atualiza uma categoria existente.

    Parâmetros:
        request (HttpRequest): Requisição HTTP contendo os dados da categoria.
        id (int): ID da categoria a ser atualizada.

    Retorna:
        HttpResponseRedirect: Redireciona para 'setup_settings' se a categoria for atualizada com sucesso.
        HttpResponse: Renderiza o formulário de edição caso os dados sejam inválidos ou a requisição seja GET.
    """
    old_category = CategoryService.get_by_id(id)
    category_form = CategoryForm(request.POST or None, request.FILES or None, instance=old_category)
    if category_form.is_valid():
        CategoryService.update(category_form, old_category)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['category_form'] = category_form
    templatetags['old_category'] = old_category
    return render(request, 'category/category_form.html', templatetags)


@login_required
def delete_category(request, id):
    """
    Exclui uma categoria existente.

    Parâmetros:
        request (HttpRequest): Requisição HTTP de confirmação de exclusão.
        id (int): ID da categoria a ser excluída.

    Retorna:
        HttpResponseRedirect: Redireciona para 'setup_settings' se a categoria for excluída com sucesso.
        HttpResponse: Renderiza a página de confirmação de exclusão caso a requisição seja GET.
    """
    category = CategoryService.get_by_id(id)
    if request.method == 'POST':
        CategoryService.delete(category)
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['category'] = category
    templatetags['exclusion_form'] = ExclusionForm()
    return render(request, 'category/exclusion_confirmation_category.html', templatetags)
