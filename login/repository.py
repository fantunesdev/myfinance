from statement.entities.next_month_view import NextMonthView
from statement.services import next_month_view_services


def create_next_year_view(user):
    next_year_view = NextMonthView(day=1, active=False, user=user)
    next_month_view_services.create_next_month_view(next_year_view)
