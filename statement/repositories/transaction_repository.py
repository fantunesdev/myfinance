import pprint
from datetime import date

from dateutil.relativedelta import relativedelta

from statement.entities.installment import Installment
from statement.forms.transaction_forms import *
from statement.services import (
    account_services,
    fixed_expenses_services,
    installment_services,
    transaction_services,
)


def validate_form_by_type(type, *args):
    """
    Valida e retorna um formulário de receita ou de despesa com base no tipo de transação.

    Args:
        type (str): O tipo de transação ('entrada' ou 'saída').
        *args: Argumentos adicionais a serem passados para o formulário de transação.

    Returns:
        TransactionRevenueForm or TransactionExpenseForm: Um formulário de transação adequado 
        com base no tipo fornecido.
    """
    if type == 'entrada':
        return TransactionRevenueForm(*args)
    return TransactionExpenseForm(*args)


def validate_account_balance(transaction):
    """
    Valida e atualiza o saldo da conta associada à transação.

    Esta função verifica se a transação está associada a uma conta e, se estiver, atualiza o 
    saldo da conta de acordo com o tipo de transação.

    Args:
        transaction (Transaction): A transação para validar e atualizar o saldo da conta.

    Returns:
        None
    """
    if transaction.account:
        if transaction.type == 'entrada':
            deposit(transaction.account, transaction.value)
        else:
            withdraw(transaction.account, transaction.value)


def validate_account_balance_when_delete_transaction(transaction):
    """
    Valida e atualiza o saldo da conta ao excluir uma transação.

    Esta função verifica se a transação está associada a uma conta e, se estiver, atualiza 
    o saldo da conta ao excluir a transação, revertendo o valor correspondente.

    Args:
        transaction (Transaction): A transação a ser excluída e a conta associada para atualizar
        o saldo.

    Returns:
        None
    """
    if transaction.account:
        if transaction.type == 'entrada':
            withdraw(transaction.account, transaction.value)
        else:
            deposit(transaction.account, transaction.value)


def validate_new_account_balance(
    old_transaction, new_transaction, old_transaction_copy
):
    """
    Valida e atualiza o saldo da conta ao editar uma transação.

    Esta função verifica se as transações antigas e novas estão associadas a uma conta e, se
    estiverem, atualiza o saldo da conta com base nas alterações realizadas.

    Args:
        old_transaction (Transaction): A transação original antes da edição.
        new_transaction (Transaction): A transação editada.
        old_transaction_copy (Transaction): Uma cópia da transação original para manipulação 
        do saldo.

    Returns:
        None
    """
    if new_transaction.account:
        if old_transaction.type == 'entrada':
            withdraw(old_transaction_copy.account, old_transaction_copy.value)
            if old_transaction_copy.account == new_transaction.account:
                new_transaction.account.balance = (
                    old_transaction_copy.account.balance
                )
            deposit(new_transaction.account, new_transaction.value)
        else:
            if old_transaction_copy.card:
                account = account_services.get_account_by_id(
                    new_transaction.account.id, new_transaction.user
                )
                old_transaction_copy.account = account
            deposit(old_transaction_copy.account, old_transaction_copy.value)
            if old_transaction_copy.account == new_transaction.account:
                new_transaction.account.balance = (
                    old_transaction_copy.account.balance
                )
            withdraw(new_transaction.account, new_transaction.value)


def withdraw(account, value):
    """
    Realiza uma retirada do valor especificado da conta.

    Args:
        account (Account): A conta da qual deseja-se retirar o valor.
        value (float): O valor a ser retirado da conta.

    Returns:
        None
    """
    account_services.withdraw(account, value)


def deposit(account, value):
    """
    Realiza um depósito do valor especificado na conta.

    Args:
        account (Account): A conta na qual deseja-se depositar o valor.
        value (float): O valor a ser depositado na conta.

    Returns:
        None
    """
    account_services.deposit(account, value)


def validate_installment(transaction):
    """
    Valida se uma transação deve ser dividida em parcelas ou tratada como uma única transação.

    Esta função verifica se o número de parcelas da transação é maior que zero. Se for, a função
    piecemeal é chamada para dividir a transação em parcelas mensais e criar transações separadas 
    para cada parcela. Caso contrário, a transação é criada como uma única transação no banco 
    de dados.

    Args:
        transaction (Transaction): Um objeto de transação a ser validado.

    Returns:
        None
    """
    if transaction.installments_number > 0:
        piecemeal(transaction)
    else:
        transaction_services.create_transaction(transaction)


def piecemeal(transaction):
    """
    Divide uma transação em parcelas mensais e as cria como transações separadas.

    Esta função cria parcelas de uma transação e as insere no banco de dados como transações
    separadas. A data de pagamento de cada parcela é calculada com base na função add_month.

    Args:
        transaction (Transaction): Um objeto de transação a ser dividido em parcelas.

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
    Adiciona um mês à data de pagamento da transação.

    Esta função calcula a data de pagamento da transação, levando em consideração se a transação
    foi feita com cartão ou em dinheiro, e se há repetição mensal da transação.

    Args:
        transaction (Transaction): Um objeto de transação contendo informações sobre a transação,
        incluindo a data de lançamento e o método de pagamento (cartão ou dinheiro).
        repetition (int): Um valor indicando o número de repetições mensais da transação.

    Returns:
        datetime.date: A data de pagamento atualizada da transação após adicionar um mês.
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


def calculate_total_revenue_expenses(transactions):
    """
    Calcula o total de receita, despesas, pagamentos com cartão, pagamentos em dinheiro e
    despesas fixas.

    Args:
        transactions (list): Uma lista de objetos de transação.

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
            if (
                transaction.category.id == 5
            ):   # Força a contagem para categorias do tipo Aplicação
                expenses += transaction.value
        else:   # Entradas
            revenue += transaction.value
    if transactions:
        fixed_expenses = fixed_expenses_services.get_fixed_expenses(
            transactions[0].user
        )
        for fixed_expense in fixed_expenses:
            fixed += fixed_expense.value
    return revenue, expenses, cards, cash, fixed
