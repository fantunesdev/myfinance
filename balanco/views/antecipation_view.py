from django.shortcuts import redirect, render

from balanco.entidades.antecipation import Antecipation
from balanco.forms import antecipation_form
from balanco.services import antecipation_service
from balanco.views.movimentacao_view import templatetags


def create_antecipation(request):
    if request.method == 'POST':
        form_antecipation = antecipation_form.AntecipationForm(request.POST)
        if form_antecipation.is_valid():
            new_antecipation = Antecipation(
                day=form_antecipation.cleaned_data['day'],
                active=form_antecipation.cleaned_data['active'],
                user=request.user
            )
            antecipation_service.create_antecipation(new_antecipation)
            return redirect('listar_mes_atual')
        else:
            print(form_antecipation.errors)
    else:
        form_antecipation = antecipation_form.AntecipationForm()
    templatetags['form_antecipation'] = form_antecipation
    return render(request, 'antecipation/form_antecipation.html', templatetags)


def update_antecipation(request):
    old_antecipation = antecipation_service.read_atecipation_user(request.user)
    form_antecipation = antecipation_form.AntecipationForm(request.POST or None, instance=old_antecipation)
    if form_antecipation.is_valid():
        new_antecipation = Antecipation(
                day=form_antecipation.cleaned_data['day'],
                active=form_antecipation.cleaned_data['active'],
                user=request.user
        )
        antecipation_service.update_antecipation(old_antecipation, new_antecipation)
        return redirect('listar_mes_atual')
    templatetags['old_antecipation'] = old_antecipation
    templatetags['form_antecipation'] = form_antecipation
    return render(request, 'antecipation/form_antecipation.html', templatetags)
