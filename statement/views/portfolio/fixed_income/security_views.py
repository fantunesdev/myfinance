from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from statement.forms.portfolio.fixed_income.fixed_income_security_form import FixedIncomeSecurityForm
from statement.forms.general_forms import ExclusionForm
from statement.models import FixedIncomeSecurity
from statement.repositories.templatetags_repository import set_menu_templatetags, set_templatetags


@login_required
def create_fixed_income_security(request):
    """
    Cria um instrumento de renda fixa.

    Exemplo:
        CDB, LCI, LCA, CRI, CRA, etc

    Parâmetros:
        request (HttpRequest): Objeto da requisição HTTP, contendo os dados da requisição

    Retorna:
        HttpResponse para o setup settings..
    """
    if request.method == 'POST':
        security_form = FixedIncomeSecurityForm(request.POST)
        if security_form.is_valid():
            security_form.save()
            return redirect('setup_settings')
    else:
        security_form = FixedIncomeSecurityForm()
    print(security_form)
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['security_form'] = security_form
    return render(request, 'portfolio/fixed_income/security/security_form.html', templatetags)



@login_required
def update_fixed_income_security(request, id):
    """
    Atualiza um instrumento de renda fixa.

    Parâmetros:
        request (HttpRequest): Objeto da requisição HTTP, contendo os dados da requisição
        id {Integer}: ID do instrumento de renda fixa

    Retorna:
        HttpResponse para o setup settings.
    """
    old_security = FixedIncomeSecurity.objects.get(id=id)
    security_form = FixedIncomeSecurityForm(request.POST or None, instance=old_security)
    if security_form.is_valid():
        security_form.save()
        return redirect('setup_settings')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['security_form'] = security_form
    return render(request, 'portfolio/fixed_income/security/security_form.html', templatetags)   


@login_required
def delete_fixed_income_security(request, id):
    """
    Deleta um instrumento de renda fixa.

    Parâmetros:
        request (HttpRequest): Objeto da requisição HTTP, contendo os dados da requisição
        id {Integer}: ID do instrumento de renda fixa

    Retorna:
        HttpResponse para o setup settings.
    """
    security = FixedIncomeSecurity.objects.get(id=id)
    exclusion_form = ExclusionForm()
    if request.POST.get('confirmation'):
        security.delete()
        return redirect('list_fixed_income')
    templatetags = set_templatetags()
    set_menu_templatetags(request.user, templatetags)
    templatetags['exclusion_form'] = exclusion_form
    templatetags['security'] = security
    return render(request, 'portfolio/fixed_income/security/detail_fixed_income.html', templatetags)
