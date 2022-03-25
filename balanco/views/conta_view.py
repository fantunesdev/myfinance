from django.shortcuts import render, redirect

from balanco.entidades.conta import Conta
from balanco.forms.conta_form import ContaForm
from balanco.forms.general_form import ExclusaoForm
from balanco.services import conta_service


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
                tela_inicial=form_conta.cleaned_data['tela_inicial']
            )
            conta_service.cadastrar_conta(conta)
            return redirect('configurar')
    else:
        form_conta = ContaForm()
    return render(request, 'conta/form_conta.html', {'form_conta': form_conta})


def listar_contas(request):
    contas = conta_service.listar_contas()
    return render(request, 'conta/listar.html', {'contas': contas})


def listar_conta_id(request, id):
    return render(request, 'conta/form_conta.html', {})


def editar_conta(request, id):
    conta_antiga = conta_service.listar_conta_id(id)
    form_conta = ContaForm(request.POST or None, instance=conta_antiga)
    if form_conta.is_valid():
        conta_nova = Conta(
            banco=form_conta.cleaned_data['banco'],
            agencia=form_conta.cleaned_data['agencia'],
            numero=form_conta.cleaned_data['numero'],
            saldo=form_conta.cleaned_data['saldo'],
            limite=form_conta.cleaned_data['limite'],
            tela_inicial=form_conta.cleaned_data['tela_inicial']
        )
        conta_service.editar_conta(conta_antiga, conta_nova)
        return redirect('configurar')
    return render(request, 'conta/editar.html', {'form_conta': form_conta,
                                                 'conta_antiga': conta_antiga})


def remover_conta(request, id):
    conta = conta_service.listar_conta_id(id)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        conta_service.remover_conta(conta)
        return redirect('configurar')
    print(request.POST.get('confirmacao'))
    return render(request, 'conta/confirma_exclusao.html', {'form_exclusao': form_exclusao,
                                                     'conta': conta})
