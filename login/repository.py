from statement.entities.category import Category
from statement.entities.next_month_view import NextMonthView
from statement.services import category_services, next_month_view_services

categories = [
    ['saida', 'Alimentação', '#960000', 'fa-solid fa-utensils'],
    ['entrada', 'Aporte', '#009600', 'fa-solid fa-coins'],
    ['saida', 'Casa', '#960000', 'fa-solid fa-house-chimney-window'],
    ['saida', 'Educação', '#960000', 'fa-solid fa-building-columns'],
    ['saida', 'Investimentos', '#960000', 'fa-solid fa-chart-line'],
    ['saida', 'Lazer', '#960000', 'fa-solid fa-film'],
    ['saida', 'Música', '#960000', 'fa-solid fa-music'],
    ['saida', 'Pessoal', '#960000', 'fa-solid fa-person'],
    ['saida', 'Cartão', '#960000', 'fa-solid fa-credit-card'],
    ['entrada', 'Renda Extra', '#009600', 'fa-solid fa-money-bill'],
    ['entrada', 'Salário', '#009603', 'fa-solid fa-briefcase'],
    ['saida', 'Social', '#960000', 'fa-solid fa-user-group'],
    ['saida', 'Transporte', '#960000', 'fa-solid fa-car'],
]


def create_categories(user):
    for i in categories:
        category = Category(
            type=i[0],
            description=i[1],
            color=i[2],
            icon=i[3],
            ignore=True if i[1] != 'Cartão' else False,
            user=user,
        )
        category_services.create_category(category)


def create_next_year_view(user):
    next_year_view = NextMonthView(day=1, active=False, user=user)
    next_month_view_services.create_next_month_view(next_year_view)
