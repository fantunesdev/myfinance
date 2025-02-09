from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.forms.fixed_income_form import FixedIncomeForm
from statement.forms.general_forms import ExclusionForm
from statement.models import FixedIncome
from statement.repositories.templatetags_repository import set_menu_templatetags, set_templatetags


@login_required
def create_fixed_income(request):
    """
    Cria um ativo de renda fixa para o usuário autenticado.

    Parâmetros:
        request (HttpRequest): Objeto da requisição HTTP, contendo os dados da requisição

    Retorna:
        HttpResponse com o formulário ou redireciona para `list_fixed_income`.
    """
    if request.method == 'POST':
        fixed_income_form = FixedIncomeForm(request.POST)
        if fixed_income_form.is_valid():
            fixed_income_asset = fixed_income_form.save(commit=False)
            fixed_income_asset.user = request.user
            fixed_income_asset.save()
            return redirect('list_fixed_income')
    else:
        fixed_income_form = FixedIncomeForm()
        print(fixed_income_form)
    template_tags = set_templatetags()
    set_menu_templatetags(request.user, template_tags)
    template_tags['fixed_income_form'] = fixed_income_form
    return render(request, 'portfolio/fixed_income/fixed_income_form.html', template_tags)



@login_required
def list_fixed_income(request):
    """
    Lista os ativos de renda fixa do usuário autenticado.

    Parâmetros:
        request (HttpRequest): Objeto da requisição HTTP, contendo os dados da requisição

    Retorna:
        HttpResponse com a listagem de ativos.
    """
    fixed_income_assets = FixedIncome.objects.filter(user=request.user)
    templatetags = set_templatetags()
    templatetags['fixed_income_assets'] = fixed_income_assets
    set_menu_templatetags(request.user, templatetags)
    return render(request, 'portfolio/fixed_income/get_fixed_income.html', templatetags)


@login_required
def detail_fixed_income(request, id):
    """
    Detalha o ativo de renda fixa do usuário autenticado.

    Parâmetros:
        request (HttpRequest): Objeto da requisição HTTP, contendo os dados da requisição
        id {Integer}: ID do investimento de renda fixa

    Retorna:
        HttpResponse com a listagem de ativos.
    """
    fixed_income_asset = FixedIncome.objects.filter(id=id, user=request.user).first()
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['fixed_income_asset'] = fixed_income_asset
    return render(request, 'portfolio/fixed_income/detail_fixed_income.html', templatetags)


@login_required
def update_fixed_income(request, id):
    """
    Atualiza o ativo de renda fixa do usuário autenticado.

    Parâmetros:
        request (HttpRequest): Objeto da requisição HTTP, contendo os dados da requisição
        id {Integer}: ID do investimento de renda fixa

    Retorna:
        HttpResponse com a listagem de ativos.
    """
    old_fixed_income_asset = FixedIncome.objects.filter(id=id, user=request.user).first()
    fixed_income_form = FixedIncomeForm(request.POST or None, instance=old_fixed_income_asset)
    if fixed_income_form.is_valid():
        fixed_income_asset = fixed_income_form.save(commit=False)
        fixed_income_asset.user = request.user
        fixed_income_asset.save()
        return redirect('list_fixed_income')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['fixed_income_form'] = fixed_income_form
    return render(request, 'portfolio/fixed_income/fixed_income_form.html', templatetags)


@login_required
def delete_fixed_income(request, id):
    """
    Deleta o ativo de renda fixa do usuário autenticado.

    Parâmetros:
        request (HttpRequest): Objeto da requisição HTTP, contendo os dados da requisição
        id {Integer}: ID do investimento de renda fixa

    Retorna:
        HttpResponse com a listagem de ativos.
    """
    fixed_income_asset = FixedIncome.objects.filter(id=id, user=request.user).first()
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        fixed_income_asset.delete()
        return redirect('list_fixed_income')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['exclusion_form'] = exclusion_form
    templatetags['fixed_income_asset'] = fixed_income_asset
    return render(request, 'portfolio/fixed_income/detail_fixed_income.html', templatetags)
