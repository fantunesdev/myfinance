from statement.models import Account, Transaction


def create_account(account):
    new_account = Account.objects.create(
        bank=account.bank,
        branch=account.branch,
        number=account.number,
        balance=account.balance,
        limits=account.limits,
        type=account.type,
        home_screen=account.home_screen,
        user=account.user,
    )
    return new_account


def get_accounts(user):
    return Account.objects.filter(user=user)


def get_account_by_id(id, user):
    return Account.objects.get(id=id, user=user)


def get_account_by_account_number(account_number, user):
    return Account.objects.get(number=account_number, user=user)


def update_account(old_account, new_account):
    old_account.bank = new_account.bank
    old_account.branch = new_account.branch
    old_account.number = new_account.number
    old_account.balance = new_account.balance
    old_account.limits = new_account.limits
    old_account.type = new_account.type
    old_account.home_screen = new_account.home_screen
    old_account.user = new_account.user
    old_account.save(force_update=True)
    return old_account


def withdraw(account, value):
    account.balance -= value
    account.save(force_update=True)


def deposit(account, value):
    account.balance += value
    account.save(force_update=True)


def delete_account(account):
    account.delete()
