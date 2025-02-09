from datetime import date, datetime

import requests
from django_q.tasks import async_task

from statement.models import Index
from statement.services.index_services import IndexServices


def update_index_values():
    """
    Atualiza os valores do índice CDI no banco de dados com base nos dados mais recentes
    da API do Banco Central.
    """

    # rate_series = fetch_cdi_rate()

    # last_month_rate = Index.objects.filter(name='CDI').order_by('date').last()

    # if not last_month_rate:
    #     last_month_rate_date = date(1986, 7, 1)
    # else:
    #     last_month_rate_date = last_month_rate.date

    # for month_rate in rate_series:
    #     index_date = datetime.strptime(month_rate['data'], '%d/%m/%Y').date()

    #     if index_date > last_month_rate_date:
    #         new_index = Index(name='CDI', date=index_date, rate=month_rate['valor'])

    #         new_index.save()

    #     if index_date == last_month_rate_date:
    #         last_month_rate.rate = month_rate['valor']
    #         last_month_rate.save()


def fetch_cdi_rate():
    """
    Recupera a série histórica de taxas CDI a partir da API do Banco Central.
    """

    # url = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=json'
    # response = requests.get(url)
    # data = response.json()
    # return data
