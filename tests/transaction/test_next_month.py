from datetime import date
from types import SimpleNamespace

import pytest
from django.http import Http404

from api.serializers.next_month_view_serializer import NextMonthViewSerializer
from api.services.next_month_view_services import get_next_month_view
from statement.repositories.next_month_view_repository import get_current_month
from statement.services.next_month_view import NextMonthViewService


def test_missing_profile_has_no_next_month_configuration(ledger):
    assert NextMonthViewService.get(ledger.user) is None
    assert NextMonthViewService.get_all(ledger.user).first() is None
    with pytest.raises(Http404):
        get_next_month_view(ledger.user)


def test_next_month_configuration_is_created_and_updated_in_the_same_profile(ledger):
    profile = NextMonthViewService.create(ledger.user, day=20, active=True)
    assert get_next_month_view(ledger.user).day == 20
    assert NextMonthViewService.get_all(ledger.user).first().active
    updated = NextMonthViewService.create(ledger.user, day=10, active=False)
    assert updated.pk == profile.pk
    assert get_next_month_view(ledger.user).day == 10
    assert not get_next_month_view(ledger.user).active


@pytest.mark.parametrize(
    'active, day, expected',
    [
        (False, 10, date(2026, 12, 20)),
        (True, 10, date(2027, 1, 20)),
        (True, 25, date(2026, 12, 20)),
    ],
)
def test_effective_month_rolls_over_only_after_the_configured_day(ledger, mocker, active, day, expected):
    NextMonthViewService.create(ledger.user, day=day, active=active)
    mocker.patch('statement.repositories.next_month_view_repository.date').today.return_value = date(2026, 12, 20)
    assert get_current_month(ledger.user) == expected


@pytest.mark.parametrize(
    'instance, expected',
    [
        (None, {'day': None, 'active': False}),
        (SimpleNamespace(day=20, active=True), {'day': 20, 'active': True}),
        (SimpleNamespace(), {'day': None, 'active': False}),
    ],
)
def test_next_month_api_representation_is_stable(instance, expected):
    assert NextMonthViewSerializer().to_representation(instance) == expected
