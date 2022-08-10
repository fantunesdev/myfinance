from datetime import date

from dateutil.relativedelta import relativedelta

from balanco.services import antecipation_service


def get_current_month(user):
    antecipation = antecipation_service.read_atecipation_user(user)
    if antecipation.active:
        return date.today() if date.today().day < antecipation.day else date.today() + relativedelta(months=1)
    return date.today()
