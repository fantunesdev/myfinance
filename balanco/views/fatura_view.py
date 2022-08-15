from datetime import date

from dateutil.relativedelta import relativedelta
from django.shortcuts import render

from balanco.repositorios import antecipation_repository
from balanco.repositorios.movimentacao_repositorio import calcular_total_entradas_saidas
from balanco.services import conta_service, cartao_service, fatura_service


templatetags = {
    'ano_atual': date.today().year,
    'mes_atual': date.today().month,
    'ano_mes': date.today()
}


def listar_fatura_mes_atual(request, cartao_id):
    mes_atual = antecipation_repository.get_current_month(request.user)
    movimentacoes = fatura_service.listar_fatura_ano_mes(mes_atual.year, mes_atual.month, cartao_id, request.user)
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    templatetags['fixed'] = fixed
    templatetags['entradas'] = entradas
    templatetags['saidas'] = saidas
    templatetags['diferenca'] = entradas - saidas
    templatetags['cartoes'] = cartoes
    templatetags['avista'] = avista
    templatetags['movimentacoes'] = movimentacoes
    templatetags['contas'] = conta_service.listar_contas(request.user)
    templatetags['faturas'] = cartao_service.listar_cartoes(request.user)
    templatetags['ano_mes'] = mes_atual
    templatetags['mes_proximo'] = templatetags['ano_mes'] + relativedelta(months=1)
    templatetags['mes_anterior'] = templatetags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', templatetags)


def listar_fatura_ano_mes(request, cartao_id, ano, mes):
    movimentacoes = fatura_service.listar_fatura_ano_mes(ano, mes, cartao_id, request.user)
    entradas, saidas, cartoes, avista, fixed = calcular_total_entradas_saidas(movimentacoes)
    templatetags['fixed'] = fixed
    templatetags['entradas'] = entradas
    templatetags['saidas'] = saidas
    templatetags['diferenca'] = entradas - saidas
    templatetags['cartoes'] = cartoes
    templatetags['avista'] = avista
    templatetags['movimentacoes'] = movimentacoes
    templatetags['contas'] = conta_service.listar_contas(request.user)
    templatetags['faturas'] = cartao_service.listar_cartoes(request.user)
    templatetags['ano_mes'] = date(ano, mes, 1)
    templatetags['mes_proximo'] = templatetags['ano_mes'] + relativedelta(months=1)
    templatetags['mes_anterior'] = templatetags['ano_mes'] - relativedelta(months=1)
    return render(request, 'movimentacao/listar_movimentacoes.html', templatetags)

