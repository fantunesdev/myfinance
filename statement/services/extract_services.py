from statement.models import Transaction


def get_extract_by_account(account, user):
    return Transaction.objects.filter(account=account, user=user).order_by('release_date')


def get_extract_by_account_and_year(account, year, user):
    return Transaction.objects \
        .filter(payment_date__year=year, account=account, user=user) \
        .order_by('release_date')


def get_extract_by_account_year_and_month(account, year, month, user):
    return Transaction.objects \
        .filter(payment_date__year=year, payment_date__month=month, account=account, user=user) \
        .order_by('release_date')
