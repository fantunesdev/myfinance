from datetime import date

from dateutil.relativedelta import relativedelta

from statement.services import account_services, card_services


def set_templatetags():
    """
    Define as tags de modelo padrão para o contexto do template.

    Retorna um dicionário contendo as tags de modelo padrão para o contexto do template,
    incluindo o ano e mês atuais.

    Returns:
        dict: Um dicionário contendo as tags de modelo padrão.
    """
    return {
        'current_year': date.today().year,
        'current_month': date.today().month,
        'year_month': date.today(),
    }


def set_menu_templatetags(user, dictionary):
    """
    Define as tags de menu para o contexto do template.

    Adiciona as tags de menu, como extratos de conta e faturas de cartão, ao dicionário
    do contexto do template.

    Args:
        user: O usuário para o qual as tags de menu devem ser definidas.
        dictionary (dict): O dicionário do contexto do template ao qual as tags de menu devem
        ser adicionadas.

    Returns:
        None
    """
    dictionary['extracts'] = account_services.get_accounts(user)
    dictionary['invoices'] = card_services.get_cards(user)


def set_transaction_navigation_templatetags(dictionary, *args):
    """
    Define as tags de navegação de transações para o contexto do template.

    Adiciona as tags de navegação de transações, como o mês atual, mês anterior e próximo mês, ao
    dicionário do contexto do template.

    Args:
        dictionary (dict): O dicionário do contexto do template ao qual as tags de navegação de
        transações devem ser adicionadas.
        *args: Argumentos adicionais para determinar o mês e ano atual, mês anterior e próximo mês.

    Returns:
        None
    """
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
    """
    Define as tags do painel para o contexto do template.

    Adiciona as tags do painel, como receita, despesas, diferença, cartões, dinheiro e fixo,
    ao dicionário do contexto do template.

    Args:
        dictionary (dict): O dicionário do contexto do template ao qual as tags do painel devem
        ser adicionadas.
        revenue (float): A receita total.
        expenses (float): As despesas totais.
        cards (float): O total de transações com cartão.
        cash (float): O total de transações em dinheiro.
        fixed (float): O total de despesas fixas.

    Returns:
        None
    """
    dictionary['revenue'] = revenue
    dictionary['expenses'] = expenses
    dictionary['difference'] = revenue - expenses
    dictionary['cards'] = cards
    dictionary['cash'] = cash
    dictionary['fixed'] = fixed
