from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from balanco.repositorios import conta_repository
from balanco.views.movimentacao_view import template_tags
from balanco.entidades.conta import Conta
from balanco.forms.conta_form import ContaForm
from balanco.forms.general_forms import ExclusaoForm
from balanco.services import conta_service


@login_required
def cadastrar_conta(request):
    if request.method == 'POST':
        form_conta = ContaForm(request.POST)
        if form_conta.is_valid():
            conta = Conta(
                banco=form_conta.cleaned_data['banco'],
                agencia=form_conta.cleaned_data['agencia'],
                numero=form_conta.cleaned_data['numero'],
                saldo=form_conta.cleaned_data['saldo'],
                limite=form_conta.cleaned_data['limite'],
                tipo=form_conta.cleaned_data['tipo'],
                tela_inicial=form_conta.cleaned_data['tela_inicial'],
                usuario=request.user
            )
            conta_service.cadastrar_conta(conta)
            return redirect('configurar')
    else:
        form_conta = ContaForm()
    template_tags['form_conta'] = form_conta
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'conta/form_conta.html', template_tags)


@login_required
def listar_contas(request):
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'conta/listar.html', template_tags)


@login_required
def editar_conta(request, id):
    conta_antiga = conta_service.listar_conta_id(id, request.user)
    form_conta = ContaForm(request.POST or None, instance=conta_antiga)
    if form_conta.is_valid():
        conta_nova = Conta(
            banco=form_conta.cleaned_data['banco'],
            agencia=form_conta.cleaned_data['agencia'],
            numero=form_conta.cleaned_data['numero'],
            saldo=form_conta.cleaned_data['saldo'],
            limite=form_conta.cleaned_data['limite'],
            tipo=form_conta.cleaned_data['tipo'],
            tela_inicial=form_conta.cleaned_data['tela_inicial'],
            usuario=request.user
        )
        conta_repository.definir_tela_inicial(conta_antiga.id, conta_nova.tela_inicial, request.user)
        conta_service.editar_conta(conta_antiga, conta_nova)
        return redirect('configurar')
    template_tags['form_conta'] = form_conta
    template_tags['conta_antiga'] = conta_antiga
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'conta/editar.html', template_tags)


@login_required
def remover_conta(request, id):
    conta = conta_service.listar_conta_id(id, request.user)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        conta_service.remover_conta(conta)
        return redirect('configurar')
    template_tags['form_exclusao'] = form_exclusao
    template_tags['conta'] = conta
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'conta/confirma_exclusao.html', template_tags)
