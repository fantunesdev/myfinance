from datetime import date

from dateutil.relativedelta import relativedelta

from statement.services.next_month_view import NextMonthViewService


def get_current_month(user):
    nm = NextMonthViewService.get(user)
    today = date.today()
    if nm and getattr(nm, 'active', False):
        if getattr(nm, 'day', 0) and today.day >= nm.day:
            return today + relativedelta(months=1)
    return today
