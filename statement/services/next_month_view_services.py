from statement.models import NextMonthView


def get_next_month_view_by_user(user):
    return NextMonthView.objects.get(user=user)


def update_next_month_view(old_next_month_view, new_next_month_view):
    old_next_month_view.day = new_next_month_view.day
    old_next_month_view.active = new_next_month_view.active
    old_next_month_view.user = new_next_month_view.user
    old_next_month_view.save(force_update=True)
