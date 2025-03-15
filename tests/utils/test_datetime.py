import pytest
from datetime import date, datetime, timedelta
from statement.utils.datetime import DateTimeUtils
from django.utils import timezone


class TestDateTimeUtils:

    def test_today(self):
        today = DateTimeUtils.today()
        assert today == timezone.localtime(timezone.now()).date()

    def test_now(self):
        now = DateTimeUtils.now()
        tolerance = timedelta(microseconds=100)
        assert abs(now - timezone.localtime(timezone.now())) <= tolerance

    def test_add_month_with_date(self):
        base_date = date(2025, 3, 14)
        new_date = DateTimeUtils.add_month(base_date, 1)
        expected_date = date(2025, 4, 14)
        assert new_date == expected_date

    def test_add_month_with_datetime(self):
        base_datetime = datetime(2025, 3, 14)
        new_datetime = DateTimeUtils.add_month(base_datetime, 1)
        expected_datetime = datetime(2025, 4,14)
        assert new_datetime == expected_datetime

    def test_add_month_with_string(self):
        base_date_str = '2025-03-14'
        new_date = DateTimeUtils.add_month(base_date_str, 1)
        expected_date = '2025-04-14'
        assert new_date == expected_date

    def test_add_month_invalid_format(self):
        with pytest.raises(ValueError):
            DateTimeUtils.add_month("2025-03-14", 1.5)
