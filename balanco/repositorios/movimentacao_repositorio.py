from django.shortcuts import redirect

from balanco.forms.movimentacao_form import MovimentacaoEntradaForm
from balanco.services import conta_service, movimentacao_service
from balanco.utils.balance_error import BalanceError


def sacar(movimentacao):
    try:
        conta_service.sacar(movimentacao.conta, movimentacao.valor)
        movimentacao_service.cadastrar_movimentacao(movimentacao)
        return True
    except BalanceError:
        return False


def depositar(movimentacao):
    try:
        conta_service.depositar(movimentacao.conta, movimentacao.valor)
        movimentacao_service.cadastrar_movimentacao(movimentacao)
        return True
    except:
        return False


def transferir(conta_saida, conta_entrada, valor):
    try:
        conta_service.sacar(conta_saida, valor)
        conta_service.depositar(conta_entrada, valor)
    except BalanceError:
        raise BalanceError('Não há saldo')
