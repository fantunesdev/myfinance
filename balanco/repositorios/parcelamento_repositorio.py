from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from balanco.entidades.parcelamento import Parcelamento
from balanco.repositorios import movimentacao_repositorio
from balanco.services import movimentacao_service, parcelamento_service


def adicionar_parcelas(movimentacoes, movimentacao_nova):
    # Cadastrar parcelas novas:
    indice_inicial = movimentacoes[0].numero_parcelas
    indice_final = movimentacao_nova.numero_parcelas
    if indice_inicial == 0:
        indice_inicial += 1
    movimentacao_nova.pagas = 0
    for i in range(indice_inicial, indice_final):
        movimentacao_nova.data_efetivacao = movimentacao_repositorio.somar_mes(movimentacao_nova, i)
        movimentacao_nova.pagas = i + 1
        movimentacao_nova.parcelamento = movimentacoes[0].parcelamento
        movimentacao_service.cadastrar_movimentacao(movimentacao_nova)
    # Editar parcelas antigas
    for index, movimentacao in enumerate(movimentacoes):
        movimentacao_nova.data_efetivacao = movimentacao_repositorio.somar_mes(movimentacao, index)
        movimentacao_nova.pagas = index + 1
        movimentacao_service.editar_movimentacao(movimentacao, movimentacao_nova)


def remover_parcelas(movimentacoes, movimentacao_nova):
    movimentacao_nova.pagas = 0
    movimentacao_nova.parcelamento.descricao = movimentacao_nova.descricao
    if movimentacao_nova.numero_parcelas <= 1:
        parcelamento = movimentacao_nova.parcelamento
        movimentacao_nova.numero_parcelas = 0
        movimentacao_nova.parcelamento = None
        movimentacao_nova.data_efetivacao = movimentacoes[0].data_efetivacao
        movimentacao_service.editar_movimentacao(movimentacoes[0], movimentacao_nova)
        parcelamento_service.remover_parcelamento(parcelamento)
    else:
        for index, movimentacao in enumerate(movimentacoes):
            if movimentacao.pagas <= movimentacao_nova.numero_parcelas:
                movimentacao_nova.data_efetivacao = movimentacao_repositorio.somar_mes(movimentacao, index)
                movimentacao_nova.pagas = index + 1
                movimentacao_service.editar_movimentacao(movimentacao, movimentacao_nova)
            else:
                movimentacao_service.remover_movimentacao(movimentacao)
        parcelamento_service.editar_parcelamento(movimentacoes[0].parcelamento, movimentacao_nova.parcelamento)


def editar_parcelas(movimentacoes, movimentacao_nova, reordenar_datas_lancamento):
    movimentacao_nova.parcelamento.descricao = movimentacao_nova.descricao
    for index, movimentacao in enumerate(movimentacoes):
        if bool(reordenar_datas_lancamento):
            movimentacao_nova.data_efetivacao = movimentacao_repositorio.somar_mes(movimentacao, index)
        movimentacao_nova.pagas = index + 1
        movimentacao_service.editar_movimentacao(movimentacao, movimentacao_nova)
        parcelamento_service.editar_parcelamento(movimentacoes[0].parcelamento, movimentacao_nova.parcelamento)


def editar_parcelamento(movimentacoes, movimentacao_nova, *args):
    aumentar_numero_parcelas = movimentacoes[0].numero_parcelas < movimentacao_nova.numero_parcelas
    diminuir_numero_parcelas = movimentacoes[0].numero_parcelas > movimentacao_nova.numero_parcelas

    if aumentar_numero_parcelas:
        adicionar_parcelas(movimentacoes, movimentacao_nova)
    elif diminuir_numero_parcelas:
        remover_parcelas(movimentacoes, movimentacao_nova)
    else:
        editar_parcelas(movimentacoes, movimentacao_nova, args)


def validar_parcelamento(movimentacao_antiga, movimentacao_nova):
    adicionar_parcelas = movimentacao_antiga.numero_parcelas < movimentacao_nova.numero_parcelas
    remover_parcelas = movimentacao_antiga.numero_parcelas > movimentacao_nova.numero_parcelas

    if adicionar_parcelas:
        if not movimentacao_antiga.parcelamento:
            parcelamento = Parcelamento(date.today(), movimentacao_nova.descricao, movimentacao_nova.usuario)
            parcelamento_db = parcelamento_service.cadastrar_parcelamento(parcelamento)
            movimentacao_antiga.parcelamento = parcelamento_db
        editar_parcelamento([movimentacao_antiga], movimentacao_nova)
    elif remover_parcelas:
        movimentacoes = movimentacao_service.listar_movimentacoes_parcelamento(movimentacao_antiga.parcelamento)
        editar_parcelamento(movimentacoes, movimentacao_nova)
    else:
        movimentacao_service.editar_movimentacao(movimentacao_antiga, movimentacao_nova)


def adiantar_parcelas(quantidade, data_inicial, parcelas):
    adiantadas = 0
    nao_adiantadas = 0
    if data_inicial > parcelas[0].data_lancamento:
        proximo_vencimento = encontrar_proximo_vencimento_cartao(parcelas[0].cartao, data_inicial)
    else:
        proximo_vencimento = encontrar_proximo_vencimento_cartao(parcelas[0].cartao, parcelas[0].data_lancamento)
    for index, parcela in enumerate(parcelas):
        if parcela.data_efetivacao > data_inicial:
            if adiantadas < quantidade:
                parcela.data_efetivacao = proximo_vencimento
                movimentacao_service.editar_movimentacao(parcela, parcela)
                adiantadas += 1
            else:
                nao_adiantadas += 1
                parcela.data_efetivacao = proximo_vencimento + relativedelta(months=nao_adiantadas)
                movimentacao_service.editar_movimentacao(parcela, parcela)


def encontrar_proximo_vencimento_cartao(cartao, data):
    proximo_vencimento = date(data.year, data.month, cartao.vencimento)
    proximo_fechamento = date(data.year, data.month, cartao.fechamento)
    if data > proximo_fechamento:
        proximo_vencimento += relativedelta(months=1)
    return proximo_vencimento

