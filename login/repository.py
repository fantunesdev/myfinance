from statement.services.next_month_view import NextMonthViewService


def create_next_year_view(user):
    NextMonthViewService.create(day=1, active=False, user=user)
