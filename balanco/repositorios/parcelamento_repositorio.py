from balanco.repositorios import movimentacao_repositorio
from balanco.services import movimentacao_service


def editar_parcelamento(movimentacoes, movimentacao_nova):
    if movimentacoes[0].numero_parcelas == movimentacao_nova.numero_parcelas:
        for index, movimentacao in enumerate(movimentacoes):
            movimentacao_nova.data_efetivacao = movimentacao_repositorio.somar_mes(movimentacao, index)
            movimentacao_nova.pagas = index + 1
            movimentacao_service.editar_movimentacao(movimentacao, movimentacao_nova)
    elif movimentacoes[0].numero_parcelas > movimentacao_nova.numero_parcelas:
        for index, movimentacao in enumerate(movimentacoes):
            if movimentacao.pagas <= movimentacao_nova.numero_parcelas:
                movimentacao_nova.data_efetivacao = movimentacao_repositorio.somar_mes(movimentacao, index)
                movimentacao_nova.pagas = index + 1
                movimentacao_service.editar_movimentacao(movimentacao, movimentacao_nova)
            else:
                movimentacao_service.remover_movimentacao(movimentacao)
    else:
        indice_inicial = movimentacoes[0].numero_parcelas + 1
        indice_final = movimentacao_nova.numero_parcelas + 1
        for i in range(indice_inicial, indice_final):
            movimentacao_nova.data_efetivacao = movimentacao_repositorio.somar_mes(movimentacao_nova, i)
            movimentacao_nova.pagas = i + 1
            movimentacao_nova.parcelamento = movimentacoes[0].parcelamento
            movimentacao_service.cadastrar_movimentacao(movimentacao_nova)
        for index, movimentacao in enumerate(movimentacoes):
            movimentacao_nova.data_efetivacao = movimentacao_repositorio.somar_mes(movimentacao, index)
            movimentacao_nova.pagas = index + 1
            movimentacao_service.editar_movimentacao(movimentacao, movimentacao_nova)
