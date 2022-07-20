from datetime import date

from dateutil.relativedelta import relativedelta


def somar_mes(movimentacao, repeticao):
    if movimentacao.cartao:
        movimentacao.data_efetivacao = date(
            movimentacao.data_lancamento.year,
            movimentacao.data_lancamento.month,
            movimentacao.cartao.vencimento
        )
        if movimentacao.data_lancamento.day >= movimentacao.cartao.fechamento:
            movimentacao.data_efetivacao += relativedelta(months=1)
        movimentacao.data_efetivacao += relativedelta(months=repeticao)
    else:
        if repeticao == 0:
            movimentacao.data_efetivacao += relativedelta(months=0)
        else:
            movimentacao.data_efetivacao += relativedelta(months=1)
    return movimentacao.data_efetivacao