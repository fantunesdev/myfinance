import random
import string

from datetime import date
from dateutil.relativedelta import relativedelta

from balanco.services import conta_service, movimentacao_service
from balanco.utils.balance_error import BalanceError


def sacar(conta, valor):
    try:
        conta_service.sacar(conta, valor)
    except BalanceError:
        raise BalanceError('Não há saldo')


def depositar(conta, valor):
    try:
        conta_service.depositar(conta, valor)
    except:
        raise


def transferir(conta_saida, conta_entrada, valor):
    try:
        conta_service.sacar(conta_saida, valor)
        conta_service.depositar(conta_entrada, valor)
    except BalanceError:
        raise BalanceError('Não há saldo')


def parcelar(movimentacao):
    parcelas = []
    descricao = movimentacao.descricao
    for i in range(0, movimentacao.numero_parcelas):
        movimentacao.pagamento = somar_mes(movimentacao, i)
        movimentacao.pagas += 1
        movimentacao.descricao = f'{descricao} ({movimentacao.pagas}/{movimentacao.numero_parcelas})'
        parcela = movimentacao_service.cadastrar_movimentacao(movimentacao)
        parcelas.append(parcela)
    return parcelas


def somar_mes(movimentacao, repeticao):
    if movimentacao.cartao:
        movimentacao.data_efetivacao = date(movimentacao.data_lancamento.year,
                                            movimentacao.data_lancamento.month,
                                            movimentacao.cartao.vencimento)
        if movimentacao.data_lancamento.day >= movimentacao.cartao.fechamento:
            movimentacao.data_efetivacao += relativedelta(months=1)
        movimentacao.data_efetivacao += relativedelta(months=repeticao)
    else:
        if repeticao == 0:
            movimentacao.data_efetivacao += relativedelta(months=0)
        else:
            movimentacao.data_efetivacao += relativedelta(months=1)
    return movimentacao.data_efetivacao


def criar_id_parcela():
    id_parcela = ''
    for i in range(8):
        id_parcela += random.choice(string.ascii_letters + string.digits)
    return id_parcela
