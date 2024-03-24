from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.db.models import Q

from statement.models import Transaction


def create_transaction(transaction):
    new_transaction = Transaction.objects.create(
        release_date=transaction.release_date,
        payment_date=transaction.payment_date,
        account=transaction.account,
        card=transaction.card,
        category=transaction.category,
        subcategory=transaction.subcategory,
        description=transaction.description,
        value=transaction.value,
        installments_number=transaction.installments_number,
        paid=transaction.paid,
        fixed=transaction.fixed,
        annual=transaction.annual,
        currency=transaction.currency,
        observation=transaction.observation,
        remember=transaction.remember,
        type=transaction.type,
        effected=transaction.effected,
        home_screen=transaction.home_screen,
        user=transaction.user,
        installment=transaction.installment,
    )
    return new_transaction


def get_transactions(user):
    return Transaction.objects.filter(user=user, home_screen=True).order_by('payment_date')


def get_transactions_by_year(year, user):
    return Transaction.objects.filter(
        payment_date__year=year, user=user, home_screen=True
    ).order_by('payment_date')


def get_last_twelve_months_transactions_by_year_and_month(year, month, user):
    end_date = datetime(year, month, 1)
    start_date = end_date - relativedelta(months=11)
    print(start_date)
    print(end_date)
    return Transaction.objects.filter(
        Q(payment_date__gte=start_date) & Q(payment_date__lte=end_date),
        user=user,
        home_screen=True
    ).order_by('release_date')


def get_transactions_by_year_and_month(year, month, user):
    return Transaction.objects.filter(
        payment_date__year=year,
        payment_date__month=month,
        user=user,
        home_screen=True,
    ).order_by('release_date')


def get_fixed_transactions_by_year_and_month(year, month, user):
    return Transaction.objects.filter(
        payment_date__year=year,
        payment_date__month=month,
        user=user,
        home_screen=True,
        fixed=True,
    ).order_by('release_date')


def get_transactions_by_description(description, user):
    return Transaction.objects.filter(
        description__icontains=description, user=user
    )


def get_transaction_by_id(id, user):
    return Transaction.objects.get(id=id, user=user)


def update_transaction(old_transaction, new_transaction):
    old_transaction.release_date = new_transaction.release_date
    old_transaction.payment_date = new_transaction.payment_date
    old_transaction.account = new_transaction.account
    old_transaction.card = new_transaction.card
    old_transaction.category = new_transaction.category
    old_transaction.subcategory = new_transaction.subcategory
    old_transaction.description = new_transaction.description
    old_transaction.value = new_transaction.value
    old_transaction.installments_number = new_transaction.installments_number
    old_transaction.paid = new_transaction.paid
    old_transaction.fixed = new_transaction.fixed
    old_transaction.annual = new_transaction.annual
    old_transaction.currency = new_transaction.currency
    old_transaction.observation = new_transaction.observation
    old_transaction.remember = new_transaction.remember
    old_transaction.type = new_transaction.type
    old_transaction.effected = new_transaction.effected
    old_transaction.home_screen = new_transaction.home_screen
    old_transaction.user = new_transaction.user
    old_transaction.installment = new_transaction.installment
    old_transaction.save(force_update=True)


def set_transaction(transaction):
    transaction.save(force_update=True)


def delete_transaction(transaction):
    transaction.delete()
