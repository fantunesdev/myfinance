import copy
from datetime import date

from django.shortcuts import redirect, render

from balanco.entidades.movimentacao import Movimentacao
from balanco.forms.general_form import ExclusaoForm
from balanco.forms.movimentacao_form import MovimentacaoSaidaForm, MovimentacaoEntradaForm
from balanco.repositorios.movimentacao_repositorio import *
from balanco.services import movimentacao_service, banco_service, bandeira_service, categoria_service, conta_service, \
    cartao_service

template_tags = {
    'ano_atual': date.today().year,
    'mes_atual': date.today().month
}


def cadastrar_movimentacao(request, tipo):
    if tipo == 'entrada':
        form = lambda *args: MovimentacaoEntradaForm(*args)
    else:
        form = lambda *args: MovimentacaoSaidaForm(*args)

    if request.method == 'POST':
        form_movimentacao = form(request.POST)
        if form_movimentacao.is_valid():
            movimentacao = Movimentacao(
                data=form_movimentacao.cleaned_data['data'],
                conta=form_movimentacao.cleaned_data['conta'],
                cartao=form_movimentacao.cleaned_data['cartao'],
                categoria=form_movimentacao.cleaned_data['categoria'],
                descricao=form_movimentacao.cleaned_data['descricao'],
                valor=form_movimentacao.cleaned_data['valor'],
                parcelas=form_movimentacao.cleaned_data['parcelas'],
                pagas=form_movimentacao.cleaned_data['pagas'],
                fixa=form_movimentacao.cleaned_data['fixa'],
                moeda=form_movimentacao.cleaned_data['moeda'],
                observacao=form_movimentacao.cleaned_data['observacao'],
                lembrar=form_movimentacao.cleaned_data['lembrar'],
                tipo=tipo,
                efetivado=form_movimentacao.cleaned_data['efetivado'],
                tela_inicial=form_movimentacao.cleaned_data['tela_inicial'],
                usuario=request.user
            )

            if not movimentacao.conta:
                if tipo == 'entrada':
                    depositar(movimentacao.conta, movimentacao.valor)
                else:
                    sacar(movimentacao.conta, movimentacao.valor)

            movimentacao_service.cadastrar_movimentacao(movimentacao)
            return redirect('listar_movimentacoes')
        else:
            print(form_movimentacao.errors)
    else:
        form_movimentacao = form()
    template_tags['form_movimentacao'] = form_movimentacao
    template_tags['tipo'] = tipo
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/form_movimentacao.html', template_tags)


def listar_movimentacoes(request):
    template_tags['movimentacoes'] = movimentacao_service.listar_movimentacoes(request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/listar.html', template_tags)


def listar_movimentacoes_conta_id(request, id):
    template_tags['movimentacoes'] = movimentacao_service.listar_movimentacoes_conta_id(id, request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/listar.html', template_tags)


def editar_movimentacao(request, id):
    movimentacao_antiga = movimentacao_service.listar_movimentacao_id(id, request.user)
    if movimentacao_antiga.tipo == 'entrada':
        form_movimentacao = MovimentacaoEntradaForm(request.POST or None, instance=movimentacao_antiga)
    else:
        form_movimentacao = MovimentacaoSaidaForm(request.POST or None, instance=movimentacao_antiga)
    copia_movimentacao_antiga = copy.deepcopy(movimentacao_antiga)
    if form_movimentacao.is_valid():
        movimentacao_nova = Movimentacao(
            data=form_movimentacao.cleaned_data['data'],
            conta=form_movimentacao.cleaned_data['conta'],
            cartao=form_movimentacao.cleaned_data['cartao'],
            categoria=form_movimentacao.cleaned_data['categoria'],
            descricao=form_movimentacao.cleaned_data['descricao'],
            valor=form_movimentacao.cleaned_data['valor'],
            parcelas=form_movimentacao.cleaned_data['parcelas'],
            pagas=form_movimentacao.cleaned_data['pagas'],
            fixa=form_movimentacao.cleaned_data['fixa'],
            moeda=form_movimentacao.cleaned_data['moeda'],
            observacao=form_movimentacao.cleaned_data['observacao'],
            lembrar=form_movimentacao.cleaned_data['lembrar'],
            tipo=movimentacao_antiga.tipo,
            efetivado=form_movimentacao.cleaned_data['efetivado'],
            tela_inicial=form_movimentacao.cleaned_data['tela_inicial'],
            usuario=request.user
        )
        if movimentacao_antiga.tipo == 'entrada':
            sacar(copia_movimentacao_antiga.conta, copia_movimentacao_antiga.valor)

            if copia_movimentacao_antiga.conta == movimentacao_nova.conta:
                movimentacao_nova.conta.saldo = copia_movimentacao_antiga.conta.saldo

            depositar(movimentacao_nova.conta, movimentacao_nova.valor)
        else:
            depositar(copia_movimentacao_antiga.conta, copia_movimentacao_antiga.valor)

            if copia_movimentacao_antiga.conta == movimentacao_nova.conta:
                movimentacao_nova.conta.saldo = copia_movimentacao_antiga.conta.saldo

            sacar(movimentacao_nova.conta, movimentacao_nova.valor)

        movimentacao_service.editar_movimentacao(movimentacao_antiga, movimentacao_nova)
        return redirect('listar_movimentacoes')
    template_tags['form_movimentacao'] = form_movimentacao
    template_tags['movimentacao_antiga'] = movimentacao_antiga
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/editar.html', template_tags)


def remover_movimentacao(request, id):
    movimentacao = movimentacao_service.listar_movimentacao_id(id, request.user)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        try:
            movimentacao_service.remover_movimentacao(movimentacao)
            if movimentacao.tipo == 'entrada':
                sacar(movimentacao.conta, movimentacao.valor)
            else:
                depositar(movimentacao.conta, movimentacao.valor)
            return redirect('listar_movimentacoes')
        except:
            return False
    template_tags['form_exclusao'] = form_exclusao
    template_tags['movimentacao'] = movimentacao
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/confirma_exclusao.html', template_tags)


def configurar(request):
    template_tags['bancos'] = banco_service.listar_bancos()
    template_tags['bandeiras'] = bandeira_service.listar_bandeiras()
    template_tags['categorias'] = categoria_service.listar_categorias(request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    template_tags['movimentacoes'] = movimentacao_service.listar_movimentacoes(request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    template_tags['cartoes'] = cartao_service.listar_cartoes(request.user)
    return render(request, 'general/settings.html', template_tags)
