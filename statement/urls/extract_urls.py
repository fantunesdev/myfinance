from django.urls import path

from statement.views.extract_view import *

urlpatterns = [
    path('', get_extract_by_account, name='get_extract_by_account'),
    path(
        'mes_atual/',
        get_current_month_extract_by_account,
        name='get_current_month_extract_by_account',
    ),
    path(
        '<int:year>/',
        get_extract_by_account_and_year,
        name='get_extract_by_account_and_year',
    ),
    path(
        '<int:year>/<int:month>/',
        get_extract_by_account_year_and_month,
        name='get_extract_by_account_year_and_month',
    ),
]
