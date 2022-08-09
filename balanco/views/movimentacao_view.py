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

template_tags = {
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
    template_tags['form_movimentacao'] = form_movimentacao
    template_tags['tipo'] = tipo
    template_tags['contas'] = conta_service.listar_contas(request.user)
    try:
        if template_tags['movimentacao_antiga']:
            template_tags.pop('movimentacao_antiga')
    except KeyError:
        pass
    return render(request, 'movimentacao/form_movimentacao.html', template_tags)


def listar_movimentacoes(request):
    template_tags['movimentacoes'] = movimentacao_service.listar_movimentacoes(request.user)
    template_tags['meses'] = movimentacao_service.listar_anos_meses(request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/listar_movimentacoes.html', template_tags)


@login_required
def listar_mes_atual(request):
    mes_atual = antecipation_repository.get_current_month(request.user)
    movimentacoes = movimentacao_service.listar_movimentacoes_ano_mes(
        ano=mes_atual.year,
        mes=mes_atual.month,
        usuario=request.user
    )
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    template_tags['fixed'] = fixed
    template_tags['entradas'] = entradas
    template_tags['saidas'] = saidas
    template_tags['diferenca'] = entradas - saidas
    template_tags['cartoes'] = cartoes
    template_tags['avista'] = avista
    template_tags['movimentacoes'] = movimentacoes
    template_tags['meses'] = movimentacao_service.listar_anos_meses(request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    template_tags['ano_mes'] = mes_atual
    template_tags['mes_proximo'] = template_tags['ano_mes'] + relativedelta(months=1)
    template_tags['mes_anterior'] = template_tags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', template_tags)


def listar_movimentacoes_ano_mes(request, ano, mes):
    movimentacoes = movimentacao_service.listar_movimentacoes_ano_mes(ano, mes, request.user)
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    template_tags['fixed'] = fixed
    template_tags['entradas'] = entradas
    template_tags['saidas'] = saidas
    template_tags['diferenca'] = entradas - saidas
    template_tags['cartoes'] = cartoes
    template_tags['avista'] = avista
    template_tags['movimentacoes'] = movimentacoes
    template_tags['meses'] = movimentacao_service.listar_anos_meses(request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    template_tags['ano_mes'] = datetime.date(ano, mes, 1)
    template_tags['mes_proximo'] = template_tags['ano_mes'] + relativedelta(months=1)
    template_tags['mes_anterior'] = template_tags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', template_tags)


def listar_movimentacoes_conta_id(request, id):
    template_tags['movimentacoes'] = movimentacao_service.listar_movimentacoes_conta_id(id, request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/listar_movimentacoes.html', template_tags)


def listar_fatura(request, cartao_id, ano, mes):
    cartao = cartao_service.listar_cartao_id(cartao_id, request.user)
    movimentacoes = movimentacao_service.listar_fatura(cartao, ano, mes, request.user)
    entradas, saidas, cartoes, avista = calcular_total_entradas_saidas(movimentacoes)
    template_tags['entradas'] = entradas
    template_tags['saidas'] = saidas
    template_tags['cartoes'] = cartoes
    template_tags['avista'] = avista
    template_tags['movimentacoes'] = movimentacoes
    return render(request, 'fatura/listar_mes.html', template_tags)


def detalhar_movimentacao(request, id):
    movimentacao = movimentacao_service.listar_movimentacao_id(id, request.user)
    if movimentacao.parcelamento:
        movimentacoes = movimentacao_service.listar_movimentacoes_parcelamento(movimentacao.parcelamento)
        template_tags['movimentacoes'] = movimentacoes
    template_tags['movimentacao'] = movimentacao
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/detalhar_movimentacao.html', template_tags)


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
    template_tags['form_movimentacao'] = form_movimentacao
    template_tags['movimentacao_antiga'] = movimentacao_antiga
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/form_movimentacao.html', template_tags)


def remover_movimentacao(request, id):
    movimentacao = movimentacao_service.listar_movimentacao_id(id, request.user)
    form_exclusao = ExclusaoForm()
    if request.POST.get('confirmacao'):
        movimentacao_service.remover_movimentacao(movimentacao)
        validar_saldo_conta_delete(movimentacao)
        return redirect('listar_mes_atual')
    template_tags['form_exclusao'] = form_exclusao
    template_tags['movimentacao'] = movimentacao
    template_tags['contas'] = conta_service.listar_contas(request.user)
    return render(request, 'movimentacao/detalhar_movimentacao.html', template_tags)


def configurar(request):
    template_tags['antecipation'] = antecipation_service.read_atecipation_user(request.user)
    template_tags['bancos'] = banco_service.listar_bancos()
    template_tags['bandeiras'] = bandeira_service.listar_bandeiras()
    template_tags['cartoes'] = cartao_service.listar_cartoes(request.user)
    template_tags['categorias'] = categoria_service.listar_categorias(request.user)
    template_tags['contas'] = conta_service.listar_contas(request.user)
    template_tags['subcategorias'] = subcategoria_service.listar_subcategorias(request.user)
    return render(request, 'general/settings.html', template_tags)
