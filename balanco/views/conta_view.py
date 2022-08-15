from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from balanco.repositorios import conta_repository, antecipation_repository
from balanco.repositorios.movimentacao_repositorio import calcular_total_entradas_saidas
from balanco.views.movimentacao_view import templatetags
from balanco.entidades.conta import Conta
from balanco.forms.conta_form import ContaForm
from balanco.forms.general_forms import ExclusaoForm
from balanco.services import conta_service, cartao_service


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
    templatetags['form_conta'] = form_conta
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'conta/form_conta.html', templatetags)


@login_required
def listar_contas(request):
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'conta/listar.html', templatetags)


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
    templatetags['form_conta'] = form_conta
    templatetags['conta_antiga'] = conta_antiga
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'conta/editar.html', templatetags)


@login_required
def remover_conta(request, id):
    conta = conta_service.listar_conta_id(id, request.user)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        conta_service.remover_conta(conta)
        return redirect('configurar')
    templatetags['form_exclusao'] = form_exclusao
    templatetags['conta'] = conta
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'conta/confirma_exclusao.html', templatetags)


def listar_conta_mes_atual(request, conta_id):
    conta = conta_service.listar_conta_id(conta_id, request.user)
    mes_atual = date.today()
    movimentacoes = conta_service.listar_movimentacoes_conta_ano_mes(
        conta_id,
        mes_atual.year,
        mes_atual.month,
        request.user
    )
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    templatetags['fixed'] = fixed
    templatetags['entradas'] = entradas
    templatetags['saidas'] = saidas
    templatetags['diferenca'] = entradas - saidas
    templatetags['cartoes'] = cartoes
    templatetags['avista'] = avista
    templatetags['movimentacoes'] = movimentacoes
    templatetags['conta'] = conta
    templatetags['contas'] = conta_service.listar_contas(request.user)
    templatetags['faturas'] = cartao_service.listar_cartoes(request.user)
    templatetags['ano_mes'] = mes_atual
    templatetags['mes_proximo'] = templatetags['ano_mes'] + relativedelta(months=1)
    templatetags['mes_anterior'] = templatetags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', templatetags)


def listar_movimentacoes_conta_ano_mes(request, conta_id, ano, mes):
    conta = conta_service.listar_conta_id(conta_id, request.user)
    movimentacoes = conta_service.listar_movimentacoes_conta_ano_mes(conta_id, ano, mes, request.user)
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    templatetags['fixed'] = fixed
    templatetags['entradas'] = entradas
    templatetags['saidas'] = saidas
    templatetags['diferenca'] = entradas - saidas
    templatetags['cartoes'] = cartoes
    templatetags['avista'] = avista
    templatetags['movimentacoes'] = movimentacoes
    templatetags['conta'] = conta
    templatetags['contas'] = conta_service.listar_contas(request.user)
    templatetags['faturas'] = cartao_service.listar_cartoes(request.user)
    templatetags['ano_mes'] = date(ano, mes, 1)
    templatetags['mes_proximo'] = templatetags['ano_mes'] + relativedelta(months=1)
    templatetags['mes_anterior'] = templatetags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', templatetags)


def listar_movimentacoes_conta(request, conta_id):
    conta = conta_service.listar_conta_id(conta_id, request.user)
    movimentacoes = conta_service.listar_movimentacoes_conta(conta, request.user)
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    templatetags['fixed'] = fixed
    templatetags['entradas'] = entradas
    templatetags['saidas'] = saidas
    templatetags['diferenca'] = entradas - saidas
    templatetags['cartoes'] = cartoes
    templatetags['avista'] = avista
    templatetags['movimentacoes'] = movimentacoes
    templatetags['conta'] = conta
    templatetags['contas'] = conta_service.listar_contas(request.user)
    templatetags['faturas'] = cartao_service.listar_cartoes(request.user)
    templatetags['ano_mes'] = date.today()
    templatetags['mes_proximo'] = templatetags['ano_mes'] + relativedelta(months=1)
    templatetags['mes_anterior'] = templatetags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', templatetags)


def listar_movimentacoes_conta_ano(request, conta_id, ano):
    conta = conta_service.listar_conta_id(conta_id, request.user)
    movimentacoes = conta_service.listar_movimentacoes_conta_ano(conta, ano, request.user)
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    templatetags['fixed'] = fixed
    templatetags['entradas'] = entradas
    templatetags['saidas'] = saidas
    templatetags['diferenca'] = entradas - saidas
    templatetags['cartoes'] = cartoes
    templatetags['avista'] = avista
    templatetags['movimentacoes'] = movimentacoes
    templatetags['conta'] = conta
    templatetags['contas'] = conta_service.listar_contas(request.user)
    templatetags['faturas'] = cartao_service.listar_cartoes(request.user)
    templatetags['ano_mes'] = date.today()
    templatetags['mes_proximo'] = templatetags['ano_mes'] + relativedelta(months=1)
    templatetags['mes_anterior'] = templatetags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', templatetags)
