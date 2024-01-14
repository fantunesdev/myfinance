from datetime import date

from dateutil.relativedelta import relativedelta

from statement.services import account_services, card_services


def set_templatetags():
    return {
        'current_year': date.today().year,
        'current_month': date.today().month,
        'year_month': date.today(),
    }


def set_menu_templatetags(user, dictionary):
    dictionary['extracts'] = account_services.get_accounts(user)
    dictionary['invoices'] = card_services.get_cards(user)


def set_transaction_navigation_templatetags(dictionary, *args):
    try:
        if type(args[0]) == int:
            year = args[0]
            month = args[1]
            dictionary['year_month'] = date(year, month, 1)
        else:
            current_month = args[0]
            dictionary['year_month'] = date(
                current_month.year, current_month.month, 1
            )

        dictionary['next_month'] = dictionary['year_month'] + relativedelta(
            months=1
        )
        dictionary['previous_month'] = dictionary[
            'year_month'
        ] - relativedelta(months=1)
    except IndexError:
        year = args[0]
        dictionary['year_month'] = date.today()
        dictionary['current_year'] = year
        dictionary['next_year'] = year + 1
        dictionary['previous_year'] = year - 1
        dictionary['next_month'] = dictionary['year_month'] + relativedelta(
            months=1
        )
        dictionary['previous_month'] = dictionary[
            'year_month'
        ] - relativedelta(months=1)


def set_dashboard_templatetags(
    dictionary, revenue, expenses, cards, cash, fixed
):
    dictionary['revenue'] = revenue
    dictionary['expenses'] = expenses
    dictionary['difference'] = revenue - expenses
    dictionary['cards'] = cards
    dictionary['cash'] = cash
    dictionary['fixed'] = fixed
