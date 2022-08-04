from balanco.services import movimentacao_service


def definir_tela_inicial(conta_id, tela_inicial, usuario):
    movimentacoes = movimentacao_service.listar_movimentacoes_conta_id(conta_id, usuario)
    for movimentacao in movimentacoes:
        movimentacao.tela_inicial = tela_inicial
        movimentacao_service.editar_parcial_movimentacao(movimentacao)
