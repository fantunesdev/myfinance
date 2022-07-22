import random
import string

from datetime import date
from dateutil.relativedelta import relativedelta

from balanco.entidades.parcelamento import Parcelamento
from balanco.forms.movimentacao_form import MovimentacaoSaidaForm, MovimentacaoEntradaForm
from balanco.services import conta_service, movimentacao_service, parcelamento_service


def validar_formulario_tipo(tipo, *args):
    try:
        request = args[0]
        movimentacao_antiga = args[1]
        if tipo == 'entrada':
            return MovimentacaoEntradaForm(request.POST or None, instance=movimentacao_antiga)
        else:
            return MovimentacaoSaidaForm(request.POST or None, instance=movimentacao_antiga)
    except IndexError:
        if tipo == 'entrada':
            return MovimentacaoEntradaForm(*args)
        return MovimentacaoSaidaForm(*args)


def validar_conta_parcelamento(movimentacao):
    validar_saldo_conta(movimentacao)
    validar_parcelamento(movimentacao)


def validar_saldo_conta(movimentacao):
    if movimentacao.conta:
        if movimentacao.tipo == 'entrada':
            depositar(movimentacao.conta, movimentacao.valor)
        else:
            sacar(movimentacao.conta, movimentacao.valor)


def validar_saldo_conta_delete(movimentacao):
    if movimentacao.conta:
        if movimentacao.tipo == 'entrada':
            sacar(movimentacao.conta, movimentacao.valor)
        else:
            depositar(movimentacao.conta, movimentacao.valor)


def validar_saldo_conta_nova(movimentacao_antiga, movimentacao_nova, copia_movimentacao_antiga):
    if movimentacao_nova.conta:
        if movimentacao_antiga.tipo == 'entrada':
            sacar(copia_movimentacao_antiga.conta, copia_movimentacao_antiga.valor)
            if copia_movimentacao_antiga.conta == movimentacao_nova.conta:
                movimentacao_nova.conta.saldo = copia_movimentacao_antiga.conta.saldo
            depositar(movimentacao_nova.conta, movimentacao_nova.valor)
        else:
            depositar(copia_movimentacao_antiga.conta, copia_movimentacao_antiga.valor)
            if copia_movimentacao_antiga.conta == movimentacao_nova.conta:
                movimentacao_nova.conta.saldo = copia_movimentacao_antiga.conta.saldo
            sacar(movimentacao_nova.conta, movimentacao_nova.valor)


def sacar(conta, valor):
    conta_service.sacar(conta, valor)


def depositar(conta, valor):
    conta_service.depositar(conta, valor)


def transferir(conta_saida, conta_entrada, valor):
    conta_service.sacar(conta_saida, valor)
    conta_service.depositar(conta_entrada, valor)


def validar_parcelamento(movimentacao):
    if movimentacao.numero_parcelas > 0:
        parcelar(movimentacao)
    else:
        movimentacao_service.cadastrar_movimentacao(movimentacao)


def parcelar(movimentacao):
    parcelamento = Parcelamento(
        data_lancamento=movimentacao.data_lancamento,
        descricao=movimentacao.descricao,
        usuario=movimentacao.usuario
    )
    parcelamento_db = parcelamento_service.cadastrar_parcelamento(parcelamento)
    movimentacao.parcelamento = parcelamento_db
    for i in range(0, movimentacao.numero_parcelas):
        movimentacao.pagamento = somar_mes(movimentacao, i)
        movimentacao.pagas += 1
        movimentacao.parcela = parcelamento_db
        movimentacao_service.cadastrar_movimentacao(movimentacao)


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


def criar_id_parcela():
    id_parcela = ''
    for i in range(8):
        id_parcela += random.choice(string.ascii_letters + string.digits)
    return id_parcela
