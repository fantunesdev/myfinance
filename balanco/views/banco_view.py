from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from balanco.forms.banco_form import BancoForm
from balanco.entidades.banco import Banco
from balanco.forms.general_form import ExclusaoForm
from balanco.services import banco_service


@login_required
def cadastrar_banco(request):
    if request.method == 'POST':
        form_banco = BancoForm(request.POST, request.FILES)
        if form_banco.is_valid():
            banco = Banco(
                descricao=form_banco.cleaned_data['descricao'],
                codigo=form_banco.cleaned_data['codigo'],
                icone=form_banco.cleaned_data['icone']
            )
            banco_service.cadastrar_banco(banco)
            return redirect('configurar')
    else:
        form_banco = BancoForm()
    return render(request, 'banco/form_banco.html', {'form_banco': form_banco})


@login_required
def listar_bancos(request):
    bancos = banco_service.listar_bancos()
    return render(request, 'banco/listar.html', {'bancos': bancos})


@login_required
def editar_banco(request, id):
    banco_antigo = banco_service.listar_banco(id)
    form_banco = BancoForm(request.POST or None, instance=banco_antigo)
    if form_banco.is_valid():
        banco_novo = Banco(
            descricao=form_banco.cleaned_data['descricao'],
            codigo=form_banco.cleaned_data['codigo'],
            icone=form_banco.cleaned_data['icone']
        )
        banco_service.editar_banco(banco_antigo, banco_novo)
        return redirect('configurar')
    return render(request, 'banco/editar.html', {'form_banco': form_banco,
                                                 'banco_antigo': banco_antigo})


@login_required
def remover_banco(request, id):
    banco = banco_service.listar_banco(id)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        banco_service.remover_banco(banco)
        return redirect('configurar')
    return render(request, 'banco/confirma_exclusao.html', {'banco': banco,
                                                            'form_exclusao': form_exclusao})
