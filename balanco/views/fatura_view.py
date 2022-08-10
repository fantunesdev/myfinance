from datetime import date

from dateutil.relativedelta import relativedelta
from django.shortcuts import render

from balanco.repositorios import antecipation_repository
from balanco.repositorios.movimentacao_repositorio import calcular_total_entradas_saidas
from balanco.services import conta_service, cartao_service, fatura_service


template_tags = {
    'ano_atual': date.today().year,
    'mes_atual': date.today().month,
    'ano_mes': date.today()
}


def listar_fatura_mes_atual(request, cartao_id):
    mes_atual = antecipation_repository.get_current_month(request.user)
    movimentacoes = fatura_service.listar_fatura_ano_mes(mes_atual.year, mes_atual.month, cartao_id, request.user)
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    template_tags['fixed'] = fixed
    template_tags['entradas'] = entradas
    template_tags['saidas'] = saidas
    template_tags['diferenca'] = entradas - saidas
    template_tags['cartoes'] = cartoes
    template_tags['avista'] = avista
    template_tags['movimentacoes'] = movimentacoes
    template_tags['contas'] = conta_service.listar_contas(request.user)
    template_tags['faturas'] = cartao_service.listar_cartoes(request.user)
    template_tags['ano_mes'] = mes_atual
    template_tags['mes_proximo'] = template_tags['ano_mes'] + relativedelta(months=1)
    template_tags['mes_anterior'] = template_tags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', template_tags)


def listar_fatura_ano_mes(request, cartao_id, ano, mes):
    movimentacoes = fatura_service.listar_fatura_ano_mes(ano, mes, cartao_id, request.user)
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    template_tags['fixed'] = fixed
    template_tags['entradas'] = entradas
    template_tags['saidas'] = saidas
    template_tags['diferenca'] = entradas - saidas
    template_tags['cartoes'] = cartoes
    template_tags['avista'] = avista
    template_tags['movimentacoes'] = movimentacoes
    template_tags['contas'] = conta_service.listar_contas(request.user)
    template_tags['faturas'] = cartao_service.listar_cartoes(request.user)
    template_tags['ano_mes'] = date(ano, mes, 1)
    template_tags['mes_proximo'] = template_tags['ano_mes'] + relativedelta(months=1)
    template_tags['mes_anterior'] = template_tags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', template_tags)

