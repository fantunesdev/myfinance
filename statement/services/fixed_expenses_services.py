import calendar
from datetime import datetime

from django.db.models import Q

from ..models import FixedExpenses


def create_fixed_expense(fixed_expense):
    FixedExpenses.objects.create(
        start_date=fixed_expense.start_date,
        end_date=fixed_expense.end_date,
        description=fixed_expense.description,
        value=fixed_expense.value,
        user=fixed_expense.user,
    )


def get_fixed_expenses(user):
    return FixedExpenses.objects.filter(user=user)


def get_fixed_expenses_by_year_and_month(year, month, user):
    first_month_day = datetime(year, month, 1)
    last_month_day = datetime(year, month, calendar.monthrange(year, month)[1])

    return FixedExpenses.objects.filter(
        Q(end_date__gte=last_month_day) | Q(end_date__isnull=True),
        start_date__lte=first_month_day,
        user=user,
    )


def get_fixed_expense_by_id(id, user):
    return FixedExpenses.objects.get(id=id, user=user)


def update_fixed_expense(old_fixed_expense, new_fixed_expense):
    old_fixed_expense.start_date = new_fixed_expense.start_date
    old_fixed_expense.end_date = new_fixed_expense.end_date
    old_fixed_expense.description = new_fixed_expense.description
    old_fixed_expense.value = new_fixed_expense.value
    old_fixed_expense.user = new_fixed_expense.user
    old_fixed_expense.save(force_update=True)


def delete_fixed_expense(fixed_expense):
    fixed_expense.delete()
