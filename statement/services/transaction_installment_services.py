from statement.models import Transaction


def get_transaction_by_installment(installment):
    transaction = Transaction.objects.filter(
        installment=installment,
        installment__isnull=False,
        user=installment.user,
    )
    return transaction
