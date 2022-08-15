import copy
import datetime
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from balanco.entidades.movimentacao import Movimentacao
from balanco.forms.general_forms import *
from balanco.forms.movimentacao_form import EditarFormMovimentacao
from balanco.repositorios import parcelamento_repositorio, antecipation_repository
from balanco.repositorios.movimentacao_repositorio import *
from balanco.services import movimentacao_service, banco_service, bandeira_service, categoria_service, conta_service, \
    cartao_service, subcategoria_service, antecipation_service

templatetags = {
    'ano_atual': date.today().year,
    'mes_atual': date.today().month,
    'ano_mes': date.today()
}


def cadastrar_movimentacao(request, tipo):
    if request.method == 'POST':
        form_movimentacao = validar_formulario_tipo(tipo, request.POST)
        if form_movimentacao.is_valid():
            movimentacao = Movimentacao(
                data_lancamento=form_movimentacao.cleaned_data['data_lancamento'],
                data_efetivacao=form_movimentacao.cleaned_data['data_efetivacao'],
                conta=form_movimentacao.cleaned_data['conta'],
                cartao=form_movimentacao.cleaned_data['cartao'],
                categoria=form_movimentacao.cleaned_data['categoria'],
                subcategoria=form_movimentacao.cleaned_data['subcategoria'],
                descricao=form_movimentacao.cleaned_data['descricao'],
                valor=form_movimentacao.cleaned_data['valor'],
                numero_parcelas=form_movimentacao.cleaned_data['numero_parcelas'],
                pagas=form_movimentacao.cleaned_data['pagas'],
                fixa=form_movimentacao.cleaned_data['fixa'],
                anual=form_movimentacao.cleaned_data['anual'],
                moeda=form_movimentacao.cleaned_data['moeda'],
                observacao=form_movimentacao.cleaned_data['observacao'],
                lembrar=form_movimentacao.cleaned_data['lembrar'],
                tipo=tipo,
                efetivado=form_movimentacao.cleaned_data['efetivado'],
                tela_inicial=form_movimentacao.cleaned_data['tela_inicial'],
                usuario=request.user,
                parcelamento=None
            )
            tela_inicial = movimentacao.conta.tela_inicial if movimentacao.conta else movimentacao.cartao.tela_inicial
            movimentacao.tela_inicial = tela_inicial
            validar_conta_parcelamento(movimentacao)
            return redirect('listar_mes_atual')
    else:
        form_movimentacao = validar_formulario_tipo(tipo)
    templatetags['form_movimentacao'] = form_movimentacao
    templatetags['tipo'] = tipo
    templatetags['contas'] = conta_service.listar_contas(request.user)
    try:
        if templatetags['movimentacao_antiga']:
            templatetags.pop('movimentacao_antiga')
    except KeyError:
        pass
    return render(request, 'movimentacao/form_movimentacao.html', templatetags)


def listar_movimentacoes(request):
    templatetags['movimentacoes'] = movimentacao_service.listar_movimentacoes(request.user)
    templatetags['meses'] = movimentacao_service.listar_anos_meses(request.user)
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/listar_movimentacoes.html', templatetags)


@login_required
def listar_mes_atual(request):
    mes_atual = antecipation_repository.get_current_month(request.user)
    movimentacoes = movimentacao_service.listar_movimentacoes_ano_mes(
        ano=mes_atual.year,
        mes=mes_atual.month,
        usuario=request.user
    )
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    templatetags['fixed'] = fixed
    templatetags['entradas'] = entradas
    templatetags['saidas'] = saidas
    templatetags['diferenca'] = entradas - saidas
    templatetags['cartoes'] = cartoes
    templatetags['avista'] = avista
    templatetags['movimentacoes'] = movimentacoes
    templatetags['meses'] = movimentacao_service.listar_anos_meses(request.user)
    templatetags['contas'] = conta_service.listar_contas(request.user)
    templatetags['faturas'] = cartao_service.listar_cartoes(request.user)
    templatetags['ano_mes'] = mes_atual
    templatetags['mes_proximo'] = templatetags['ano_mes'] + relativedelta(months=1)
    templatetags['mes_anterior'] = templatetags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', templatetags)


def listar_movimentacoes_ano(request, ano):
    movimentacoes = movimentacao_service.listar_movimentacoes_ano(ano, request.user)
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    templatetags['fixed'] = fixed
    templatetags['entradas'] = entradas
    templatetags['saidas'] = saidas
    templatetags['diferenca'] = entradas - saidas
    templatetags['cartoes'] = cartoes
    templatetags['avista'] = avista
    templatetags['movimentacoes'] = movimentacoes
    templatetags['meses'] = movimentacao_service.listar_anos_meses(request.user)
    templatetags['contas'] = conta_service.listar_contas(request.user)
    templatetags['faturas'] = cartao_service.listar_cartoes(request.user)
    templatetags['ano_mes'] = date.today()
    templatetags['mes_proximo'] = templatetags['ano_mes'] + relativedelta(months=1)
    templatetags['mes_anterior'] = templatetags['ano_mes'] - relativedelta(months=1)
    templatetags['ano_atual'] = ano
    templatetags['ano_proximo'] = templatetags['ano_atual'] + 1
    templatetags['ano_anterior'] = templatetags['ano_atual'] - 1
    return render(request, 'movimentacao/listar_movimentacoes.html', templatetags)


def listar_movimentacoes_ano_mes(request, ano, mes):
    movimentacoes = movimentacao_service.listar_movimentacoes_ano_mes(ano, mes, request.user)
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    templatetags['fixed'] = fixed
    templatetags['entradas'] = entradas
    templatetags['saidas'] = saidas
    templatetags['diferenca'] = entradas - saidas
    templatetags['cartoes'] = cartoes
    templatetags['avista'] = avista
    templatetags['movimentacoes'] = movimentacoes
    templatetags['meses'] = movimentacao_service.listar_anos_meses(request.user)
    templatetags['contas'] = conta_service.listar_contas(request.user)
    templatetags['faturas'] = cartao_service.listar_cartoes(request.user)
    templatetags['ano_mes'] = datetime.date(ano, mes, 1)
    templatetags['mes_proximo'] = templatetags['ano_mes'] + relativedelta(months=1)
    templatetags['mes_anterior'] = templatetags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', templatetags)


def listar_movimentacoes_conta_id(request, id):
    templatetags['movimentacoes'] = movimentacao_service.listar_movimentacoes_conta_id(id, request.user)
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/listar_movimentacoes.html', templatetags)


def detalhar_movimentacao(request, id):
    movimentacao = movimentacao_service.listar_movimentacao_id(id, request.user)
    if movimentacao.parcelamento:
        movimentacoes = movimentacao_service.listar_movimentacoes_parcelamento(movimentacao.parcelamento)
        templatetags['movimentacoes'] = movimentacoes
    templatetags['movimentacao'] = movimentacao
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/detalhar_movimentacao.html', templatetags)


def editar_movimentacao(request, id):
    movimentacao_antiga = movimentacao_service.listar_movimentacao_id(id, request.user)
    form_movimentacao = EditarFormMovimentacao(request.POST or None, instance=movimentacao_antiga)
    copia_movimentacao_antiga = copy.deepcopy(movimentacao_antiga)
    if form_movimentacao.is_valid():
        movimentacao_nova = Movimentacao(
            data_lancamento=form_movimentacao.cleaned_data['data_lancamento'],
            data_efetivacao=form_movimentacao.cleaned_data['data_efetivacao'],
            conta=form_movimentacao.cleaned_data['conta'],
            cartao=form_movimentacao.cleaned_data['cartao'],
            categoria=form_movimentacao.cleaned_data['categoria'],
            subcategoria=form_movimentacao.cleaned_data['subcategoria'],
            descricao=form_movimentacao.cleaned_data['descricao'],
            valor=form_movimentacao.cleaned_data['valor'],
            numero_parcelas=movimentacao_antiga.numero_parcelas,
            pagas=movimentacao_antiga.pagas,
            fixa=form_movimentacao.cleaned_data['fixa'],
            anual=form_movimentacao.cleaned_data['anual'],
            moeda=form_movimentacao.cleaned_data['moeda'],
            observacao=form_movimentacao.cleaned_data['observacao'],
            lembrar=form_movimentacao.cleaned_data['lembrar'],
            tipo=form_movimentacao.cleaned_data['tipo'],
            efetivado=form_movimentacao.cleaned_data['efetivado'],
            tela_inicial=form_movimentacao.cleaned_data['tela_inicial'],
            usuario=request.user,
            parcelamento=movimentacao_antiga.parcelamento
        )
        tela_inicial = movimentacao_nova.conta.tela_inicial if movimentacao_nova.conta else movimentacao_nova.cartao.tela_inicial
        movimentacao_nova.tela_inicial = tela_inicial
        validar_saldo_conta_nova(movimentacao_antiga, movimentacao_nova, copia_movimentacao_antiga)
        if form_movimentacao.cleaned_data['parcelar'] == 'parcelar':
            parcelamento_repositorio.validar_parcelamento(copia_movimentacao_antiga, movimentacao_nova)
            return redirect('listar_mes_atual')
        else:
            movimentacao_service.editar_movimentacao(movimentacao_antiga, movimentacao_nova)
        return redirect('listar_mes_atual')
    templatetags['form_movimentacao'] = form_movimentacao
    templatetags['movimentacao_antiga'] = movimentacao_antiga
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/form_movimentacao.html', templatetags)


def remover_movimentacao(request, id):
    movimentacao = movimentacao_service.listar_movimentacao_id(id, request.user)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        movimentacao_service.remover_movimentacao(movimentacao)
        validar_saldo_conta_delete(movimentacao)
        return redirect('listar_mes_atual')
    templatetags['form_exclusao'] = form_exclusao
    templatetags['movimentacao'] = movimentacao
    templatetags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/detalhar_movimentacao.html', templatetags)


def configurar(request):
    templatetags['antecipation'] = antecipation_service.read_atecipation_user(request.user)
    templatetags['bancos'] = banco_service.listar_bancos()
    templatetags['bandeiras'] = bandeira_service.listar_bandeiras()
    templatetags['cartoes'] = cartao_service.listar_cartoes(request.user)
    templatetags['categorias'] = categoria_service.listar_categorias(request.user)
    templatetags['contas'] = conta_service.listar_contas(request.user)
    templatetags['subcategorias'] = subcategoria_service.listar_subcategorias(request.user)
    return render(request, 'general/settings.html', templatetags)
