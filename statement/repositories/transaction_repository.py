import pprint
from datetime import date

from dateutil.relativedelta import relativedelta

from statement.entities.installment import Installment
from statement.forms.transaction_forms import *
from statement.services.core.account import AccountService
from statement.services import (
    fixed_expenses_services,
    installment_services,
    transaction_services,
)


def validate_form_by_type(type, *args):
    """
    Valida e retorna um formulário de receita ou de despesa com base no tipo de lançamento.

    Args:
        type (str): O tipo de lançamento ('entrada' ou 'saída').
        *args: Argumentos adicionais a serem passados para o formulário de lançamento.

    Returns:
        TransactionRevenueForm or TransactionExpenseForm: Um formulário de lançamento adequado
        com base no tipo fornecido.
    """
    if type == 'entrada':
        return TransactionRevenueForm(*args)
    return TransactionExpenseForm(*args)


def validate_installment(transaction):
    """
    Valida se umo lançamento deve ser dividida em parcelas ou tratada como uma único lançamento.

    Esta função verifica se o número de parcelas do lançamento é maior que zero. Se for, a função
    piecemeal é chamada para dividir o lançamento em parcelas mensais e criar transações separadas
    para cada parcela. Caso contrário, o lançamento é criada como uma único lançamento no banco
    de dados.

    Args:
        transaction (Transaction): Um objeto de lançamento a ser validado.

    Returns:
        None
    """
    if transaction.installments_number > 0:
        piecemeal(transaction)
    else:
        transaction_services.create_transaction(transaction)


def piecemeal(transaction):
    """
    Divide umo lançamento em parcelas mensais e as cria como transações separadas.

    Esta função cria parcelas de umo lançamento e as insere no banco de dados como transações
    separadas. A data de pagamento de cada parcela é calculada com base na função add_month.

    Args:
        transaction (Transaction): Um objeto de lançamento a ser dividido em parcelas.

    Returns:
        None
    """
    installment = Installment(
        release_date=transaction.release_date,
        description=transaction.description,
        user=transaction.user,
    )
    installment_db = installment_services.create_installment(installment)
    transaction.installment = installment_db
    for i in range(0, transaction.installments_number):
        transaction.payment_date = add_month(transaction, i)
        transaction.paid += 1
        transaction.installment = installment_db
        transaction_services.create_transaction(transaction)


def add_month(transaction, repetition):
    """
    Adiciona um mês à data de pagamento do lançamento.

    Esta função calcula a data de pagamento do lançamento, levando em consideração se o lançamento
    foi feita com cartão ou em dinheiro, e se há repetição mensal do lançamento.

    Args:
        transaction (Transaction): Um objeto de lançamento contendo informações sobre o lançamento,
        incluindo a data de lançamento e o método de pagamento (cartão ou dinheiro).
        repetition (int): Um valor indicando o número de repetições mensais do lançamento.

    Returns:
        datetime.date: A data de pagamento atualizada do lançamento após adicionar um mês.
    """
    if transaction.card:
        transaction.payment_date = date(
            transaction.release_date.year,
            transaction.release_date.month,
            transaction.card.expiration_day,
        )
        if transaction.release_date.day >= transaction.card.closing_day:
            transaction.payment_date += relativedelta(months=1)
        transaction.payment_date += relativedelta(months=repetition)
    else:
        if repetition == 0:
            transaction.payment_date += relativedelta(months=0)
        else:
            transaction.payment_date += relativedelta(months=1)
    return transaction.payment_date


def calculate_total_revenue_expenses(transactions, year, month):
    """
    Calcula o total de receita, despesas, pagamentos com cartão, pagamentos em dinheiro e
    despesas fixas.

    Args:
        transactions (list): Uma lista de objetos de lançamento.

    Returns:
        tuple: Uma tupla contendo os seguintes valores:
            - receita (float): O total de receita.
            - despesas (float): O total de despesas.
            - cartões (float): O total de despesas pagas com cartão.
            - dinheiro (float): O total de despesas pagas em dinheiro.
            - fixo (float): O total de despesas fixas.
    """
    revenue = 0
    expenses = 0
    cards = 0
    cash = 0
    fixed = 0
    for transaction in transactions:
        if transaction.type == 'saida':   # Saídas
            if (
                not transaction.category.ignore
            ):   # Contabiliza apenas os lançamentos das categorias não ignoradas.
                # Despesas com cartão
                if transaction.card:
                    cards += transaction.value
                # Despesas à vista
                else:
                    cash += transaction.value

                # Contagem das despesas fixas
                if transaction.fixed:
                    fixed += transaction.value

                # Contagem total de gastos
                expenses += transaction.value
            if transaction.category.id == 5:   # Força a contagem para categorias do tipo Aplicação
                expenses += transaction.value
        else:   # Entradas
            revenue += transaction.value
    if transactions:
        user = transactions[0].user
        fixed_expenses = fixed_expenses_services.get_fixed_expenses_by_year_and_month(year, month, user)
        for fixed_expense in fixed_expenses:
            fixed += fixed_expense.value
    return revenue, expenses, cards, cash, fixed
