from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from django.utils import timezone


class DateTimeUtils:
    @staticmethod
    def today():
        """
        Retorna a data de hoje na timezone da aplicação (sem horário).
        """
        return timezone.localtime(timezone.now()).date()

    @staticmethod
    def now():
        """
        Retorna a data e hora atual na timezone da aplicação.
        """
        return timezone.localtime(timezone.now())

    @staticmethod
    def date(year, month, day):
        """
        Retorna uma data na timezone da aplicação
        """
        return timezone.make_aware(datetime(year, month, day, 0, 0, 0))

    @classmethod
    def add_months(cls, date_value, months: int):
        """
        Adiciona um número de meses a uma data, levando em consideração que a data pode vir de um form (string)
        ou de um model do Django (datetime.date ou datetime.datetime).

        :param date: Data a ser modificada (str, datetime.date ou datetime.datetime)
        :param months: Número de meses a adicionar
        :return: Nova data com os meses adicionados (mantendo o tipo original)
        """
        match date_value:
            case str():
                date_value = cls.string_to_date(date_value)
                date_value = date_value + relativedelta(months=months)
                return date_value.strftime('%Y-%m-%d')
            case date():
                return date_value + relativedelta(months=months)
            case datetime():
                return date_value + relativedelta(months=months)

    @staticmethod
    def string_to_date(string_date):
        """
        Transforma uma data em string em uma data datetime

        :string_date: Uma string de data no formato %Y-%m-%d
        """
        try:
            return timezone.datetime.strptime(string_date, '%Y-%m-%d').date()
        except ValueError as e:
            raise ValueError(f'Formato de data inválido. Use "YYYY-MM-DD". Erro: {e}') from e
