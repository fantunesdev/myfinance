from datetime import date

from dateutil.relativedelta import relativedelta

from statement.services import next_month_view_services


def get_current_month(user):
    next_month_view = next_month_view_services.get_next_month_view_by_user(
        user
    )
    if next_month_view.active:
        return (
            date.today()
            if date.today().day < next_month_view.day
            else date.today() + relativedelta(months=1)
        )
    return date.today()
