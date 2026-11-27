from datetime import date, timedelta
from decimal import Decimal

import pytest
import test_investment_sync as scenarios
from django.core.exceptions import ValidationError
from django.utils import timezone

from bank_sync.investments import sync_investments
from clients.pluggy.reader import ProbeError
from investments.services.investment import InvestmentService


@pytest.fixture
def sync_case(db):
    case = scenarios.PositionSyncTests()
    case.setUp()
    return case


def test_position_sync_rejects_a_concurrent_collection(sync_case):
    c = sync_case
    c.connection.lease_until = timezone.now() + timedelta(minutes=5)
    c.connection.save()
    with pytest.raises(ValidationError):
        c.sync()


def test_position_sync_rejects_a_source_changed_during_collection(sync_case, mocker):
    c = sync_case
    reader = scenarios.Reader([c.row])
    mocker.patch.object(
        reader,
        'request',
        side_effect=[
            {'status': 'UPDATED', 'executionStatus': 'SUCCESS', 'lastUpdatedAt': 'first'},
            {'status': 'UPDATED', 'executionStatus': 'SUCCESS', 'lastUpdatedAt': 'second'},
        ],
    )
    with pytest.raises(ProbeError):
        sync_investments(c.connection, reader)
    assert c.inv.transactions.count() == 1


def test_position_sync_does_not_apply_a_batch_after_the_lease_expires(sync_case, mocker):
    c = sync_case
    reader = scenarios.Reader([c.row])

    def expire(*args):
        c.connection.__class__.objects.filter(pk=c.connection.pk).update(
            lease_until=timezone.now() - timedelta(seconds=1)
        )
        return [c.row]

    mocker.patch.object(reader, 'numbered', side_effect=expire)
    with pytest.raises(ProbeError):
        sync_investments(c.connection, reader)
    assert c.inv.transactions.count() == 1


def test_older_position_never_overwrites_a_newer_reference(sync_case):
    c = sync_case
    assert c.sync()['updated'] == 1
    before = c.inv.transactions.count()
    result = c.sync([{**c.row, 'date': '2026-11-09T03:00:00Z', 'balance': 50}])
    assert result['unchanged'] == 1
    assert c.inv.transactions.count() == before
    assert InvestmentService.get_position(c.inv)['value'] == 150


def test_repeated_source_revision_requires_review_and_preserves_the_last_position(sync_case):
    c = sync_case
    c.sync()
    c.sync([{**c.row, 'balance': 160}])
    before = c.inv.transactions.count()
    with pytest.raises(ProbeError):
        c.sync()
    assert c.inv.transactions.count() == before
    assert InvestmentService.get_position(c.inv)['value'] == Decimal(160)


def test_position_sync_records_the_official_due_date(sync_case):
    c = sync_case
    c.sync([{**c.row, 'dueDate': '2027-12-15T00:00:00Z'}])
    c.inv.refresh_from_db()
    assert c.inv.due_date == date(2027, 12, 15)
