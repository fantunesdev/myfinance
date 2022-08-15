from statement.services import extract_services, transaction_services


def set_home_screen(account_id, home_screen, user):
    transactions = extract_services.get_extract_by_account(account_id, user)
    for transaction in transactions:
        transaction.home_screen = home_screen
        transaction_services.set_transaction(transaction)
