import random
import string

from datetime import date

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
    descricao = movimentacao.descricao
    for i in range(0, movimentacao.parcelas):
        movimentacao.pagamento = somar_mes(movimentacao, i)
        movimentacao.pagas += 1
        movimentacao.descricao = f'{descricao} ({movimentacao.pagas}/{movimentacao.parcelas})'
        movimentacao_service.cadastrar_movimentacao(movimentacao)


def somar_mes(movimentacao, repeticao):
    dia = movimentacao.data.day
    mes = movimentacao.data.month
    ano = movimentacao.data.year
    # Criar um campo fechamento no CRUD de cartões
    movimentacao_cartao_fechamento = 3
    if movimentacao.cartao:
        dia = movimentacao.cartao.vencimento
        if movimentacao.data.day >= movimentacao_cartao_fechamento:
            mes += 1
    if mes > 12:
        mes = 1
    else:
        mes += repeticao
    return date(ano, mes, dia)


def criar_id_parcela():
    id_parcela = ''
    for i in range(8):
        id_parcela += random.choice(string.ascii_letters + string.digits)
    return id_parcela
