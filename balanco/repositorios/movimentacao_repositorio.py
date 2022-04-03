from balanco.services import conta_service
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
