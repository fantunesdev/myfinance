from datetime import date

from dateutil.relativedelta import relativedelta

from statement.entities.installment import Installment
from statement.repositories import transaction_repository
from statement.services import transaction_services, installment_services, transaction_installment_services


def add_installments(transactions, new_transaction):
    # Cadastrar parcelas novas:
    start_index = transactions[0].installments_number
    final_index = new_transaction.installments_number
    if start_index == 0:
        start_index += 1
    new_transaction.paid = 0
    for i in range(start_index, final_index):
        new_transaction.payment_date = transaction_repository.add_month(new_transaction, i)
        new_transaction.paid = i + 1
        new_transaction.installment = transactions[0].installment
        transaction_services.create_transaction(new_transaction)
    # Editar parcelas antigas
    for index, transaction in enumerate(transactions):
        new_transaction.payment_date = transaction_repository.add_month(transaction, index)
        new_transaction.paid = index + 1
        transaction_services.update_transaction(transaction, new_transaction)


def remove_installments(transactions, new_transaction):
    new_transaction.paid = 0
    new_transaction.installment.description = new_transaction.description
    if new_transaction.installments_number <= 1:
        installment = new_transaction.installment
        new_transaction.installments_number = 0
        new_transaction.installment = None
        new_transaction.payment_date = transactions[0].payment_date
        transaction_services.update_transaction(transactions[0], new_transaction)
        installment_services.delete_installment(installment)
    else:
        for index, transaction in enumerate(transactions):
            if transaction.paid <= new_transaction.installments_number:
                new_transaction.payment_date = transaction_repository.add_month(transaction, index)
                new_transaction.paid = index + 1
                transaction_services.update_transaction(transaction, new_transaction)
            else:
                transaction_services.delete_transaction(transaction)
        installment_services.update_installment(transactions[0].installment, new_transaction.installment)


def update_installments(transactions, new_transaction, reorder_release_dates):
    new_transaction.installment.description = new_transaction.description
    for index, transaction in enumerate(transactions):
        if bool(reorder_release_dates):
            new_transaction.payment_date = transaction_repository.add_month(transaction, index)
        new_transaction.paid = index + 1
        transaction_services.update_transaction(transaction, new_transaction)
        installment_services.update_installment(transactions[0].installment, new_transaction.installment)


def update_installment(transactions, new_transaction, *args):
    increase_installments_number = transactions[0].installments_number < new_transaction.installments_number
    decrease_installments_number = transactions[0].installments_number > new_transaction.installments_number

    if increase_installments_number:
        add_installments(transactions, new_transaction)
    if decrease_installments_number:
        remove_installments(transactions, new_transaction)
    else:
        update_installments(transactions, new_transaction, args)


def validate_installment(old_transaction, new_transaction):
    add_installment = old_transaction.installments_number < new_transaction.installments_number
    remove_installment = old_transaction.installments_number > new_transaction.installments_number

    if add_installment:
        if not old_transaction.installment:
            installment = Installment(date.today(), new_transaction.description, new_transaction.user)
            installment_db = installment_services.create_installment(installment)
            old_transaction.installment = installment_db
        update_installment([old_transaction], new_transaction)
    elif remove_installment:
        transactions = transaction_installment_services.get_transaction_by_installment(old_transaction.installment)
        update_installment(transactions, new_transaction)
    else:
        transaction_services.update_transaction(old_transaction, new_transaction)


def advance_installments(quantity, initial_date, installments):
    advanced = 0
    not_advanced = 0
    if initial_date > installments[0].release_date:
        next_expiration = find_next_expiration_card_date(installments[0].card, initial_date)
    else:
        next_expiration = find_next_expiration_card_date(installments[0].card, installments[0].release_date)
    for index, installment in enumerate(installments):
        if installment.payment_date > initial_date:
            if advanced < quantity:
                installment.payment_date = next_expiration
                transaction_services.update_transaction(installment, installment)
                advanced += 1
            else:
                not_advanced += 1
                installment.payment_date = next_expiration + relativedelta(months=not_advanced)
                transaction_services.update_transaction(installment, installment)


def find_next_expiration_card_date(card, new_date):
    next_expiration_date = date(new_date.year, new_date.month, card.expiration_day)
    next_closing_date = date(new_date.year, new_date.month, card.closing_day)
    if new_date > next_closing_date:
        next_expiration_date += relativedelta(months=1)
    return next_expiration_date
