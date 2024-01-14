from statement.models import Transaction


def get_invoice_by_card_year_and_month(card, year, month, user):
    return Transaction.objects.filter(
        payment_date__year=year,
        payment_date__month=month,
        card=card,
        user=user,
    ).order_by('release_date')


def get_invoice_by_card_and_year(card, year, user):
    return Transaction.objects.filter(
        payment_date__year=year, card=card, user=user
    ).order_by('release_date')


def get_invoice_by_card(card, user):
    return Transaction.objects.filter(card=card, user=user).order_by(
        'release_date'
    )
