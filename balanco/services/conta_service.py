from ..models import Conta
from ..utils.balance_error import BalanceError


def cadastrar_conta(conta):
    Conta.objects.create(
        banco=conta.banco,
        agencia=conta.agencia,
        numero=conta.numero,
        saldo=conta.saldo,
        limite=conta.limite,
        tela_inicial=conta.tela_inicial
    )


def listar_contas():
    return Conta.objects.all()


def listar_conta_id(id):
    return Conta.objects.get(id=id)


def editar_conta(conta_antiga, conta_nova):
    conta_antiga.banco = conta_nova.banco
    conta_antiga.agencia = conta_nova.agencia
    conta_antiga.numero = conta_nova.numero
    conta_antiga.saldo = conta_nova.saldo
    conta_antiga.limite = conta_nova.limite
    conta_antiga.tipo = conta_nova.tipo
    conta_antiga.tela_inicial = conta_nova.tela_inicial
    conta_antiga.save(force_update=True)


def sacar(conta, valor):
    if conta.saldo + conta.limite - valor >= 0:
        conta.saldo -= valor
        conta.save(force_update=True)
    else:
        raise BalanceError('Não há saldo disponível.')


def depositar(conta, valor):
    conta.saldo += valor
    conta.save(force_update=True)


def remover_conta(conta):
    conta.delete()
