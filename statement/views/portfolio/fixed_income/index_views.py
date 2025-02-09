from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.forms.portfolio.fixed_income.index_form import IndexForm
from statement.forms.general_forms import ExclusionForm
from statement.services.index_services import IndexServices
from statement.repositories.templatetags_repository import set_menu_templatetags, set_templatetags


@login_required
def create_index(request):
    """
    Cria um índice financeiro.

    Exemplo:
        Selic, CDI, Etc.

    Parâmetros:
        request (HttpRequest): Objeto da requisição HTTP, contendo os dados da requisição

    Retorna:
        HttpResponse com o formulário ou redireciona para `list_fixed_income`.
    """
    if request.method == 'POST':
        index_form = IndexForm(request.POST, request.FILES)
        if index_form.is_valid():
            index_form.save()
            return redirect('setup_settings')
    else:
        index_form = IndexForm()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['index_form'] = index_form
    return render(request, 'portfolio/fixed_income/index/index_form.html', templatetags)


@login_required
def update_index(request, id):
    """
    Atualiza um índice financeiro.

    Parâmetros:
        request (HttpRequest): Objeto da requisição HTTP, contendo os dados da requisição
        id {Integer}: O ID do índice

    Retorna:
        HttpResponse com o formulário ou redireciona para `list_fixed_income`.
    """
    old_index = IndexServices.get(id=id)
    print(old_index)
    index_form = IndexForm(request.POST or None, request.FILES or None, instance=old_index)
    if index_form.is_valid():
        index_form.save()
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['index_form'] = index_form
    templatetags['old_index'] = old_index
    return render(request, 'portfolio/fixed_income/index/index_form.html', templatetags)


@login_required
def delete_index(request, id):
    """
    Exclui um índice financeiro.

    Exemplo:
        Selic, CDI, Etc.

    Parâmetros:
        request (HttpRequest): Objeto da requisição HTTP, contendo os dados da requisição
        id {Integer}: O ID do índice

    Retorna:
        HttpResponse com o formulário ou redireciona para `list_fixed_income`.
    """
    index = IndexServices.objects.get(id=id)
    if request.method == 'POST':
        index.delete()
        return redirect('setup_settings')
    exclusion_form = ExclusionForm()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['exclusion_form'] = exclusion_form
    templatetags['index'] = index
    return render(request, 'portfolio/fixed_income/index/exclusion_confirmation_index.html', templatetags)
