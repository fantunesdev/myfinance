from statement.models import Currency


def get_currency_by_id(id):
    return Currency.objects.get(id=id)
