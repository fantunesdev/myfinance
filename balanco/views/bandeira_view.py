from django.shortcuts import redirect, render

from balanco.entidades.bandeira import Bandeira
from balanco.forms.bandeira_form import BandeiraForm
from balanco.forms.general_form import ExclusaoForm
from balanco.services import bandeira_service


def cadastrar_bandeira(request):
    if request.method == 'POST':
        form_bandeira = BandeiraForm(request.POST, request.FILES)
        if form_bandeira.is_valid():
            bandeira = Bandeira(
                descricao=form_bandeira.cleaned_data['descricao'],
                icone=form_bandeira.cleaned_data['icone']
            )
            bandeira_service.cadastrar_bandeira(bandeira)
            return redirect('configurar')
    else:
        form_bandeira = BandeiraForm()
    return render(request, 'bandeira/form_bandeira.html', {'form_bandeira': form_bandeira})


def listar_bandeiras(request):
    bandeiras = bandeira_service.listar_bandeiras()
    return render(request, 'bandeira/listar.html', {'bandeiras': bandeiras})


def editar_bandeira(request, id):
    bandeira_antiga = bandeira_service.listar_bandeira_id(id)
    form_bandeira = BandeiraForm(request.POST or None, request.FILES or None, instance=bandeira_antiga)
    if form_bandeira.is_valid():
        bandeira_nova = Bandeira(
            descricao=form_bandeira.cleaned_data['descricao'],
            icone=form_bandeira.cleaned_data['icone']
        )
        bandeira_service.editar_bandeira(bandeira_antiga, bandeira_nova)
        return redirect('configurar')
    return render(request, 'bandeira/editar.html', {'form_bandeira': form_bandeira,
                                                    'bandeira_antiga': bandeira_antiga})


def remover_bandeira(request, id):
    bandeira = bandeira_service.listar_bandeira_id(id)
    if request.method == 'POST':
        bandeira_service.remover_bandeira(bandeira)
        return redirect('configurar')
    form_exclusao = ExclusaoForm()
    return render(request, 'bandeira/confirma_exclusao.html', {'bandeira': bandeira,
                                                               'form_exclusao': form_exclusao})
