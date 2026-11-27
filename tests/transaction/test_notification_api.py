from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from api.views.notification import NotificationView
from login.models import User
from statement.models import Account, AccountType, Bank, Card, CardNumber, Flag, Notification

pytestmark = pytest.mark.django_db


@pytest.fixture
def records():
    owner = User.objects.create(username='notification-owner', email='owner@notification.invalid')
    other = User.objects.create(username='notification-other', email='other@notification.invalid')
    bank = Bank.objects.create(description='Bank', app_id='bank.app')
    kind = AccountType.objects.create(description='Current')
    flag = Flag.objects.create(description='Flag')
    cards = []
    for user in (owner, other):
        account = Account.objects.create(user=user, bank=bank, type=kind)
        card = Card.objects.create(
            user=user, account=account, flag=flag, description='Card', closing_day=3, expiration_day=10
        )
        CardNumber.objects.create(card=card, number='1234 5678 9012 3456')
        cards.append(card)
    return SimpleNamespace(owner=owner, other=other, cards=cards)


def create(actor=None, **extra):
    request = APIRequestFactory().post(
        '/api/notifications/',
        {'app': 'bank.app', 'title': 'Purchase', 'message': 'Compra no cartão final 3456', **extra},
        format='json',
    )
    if actor:
        force_authenticate(request, user=actor)
    return NotificationView.as_view({'post': 'create'})(request)


def test_creation_binds_only_the_authenticated_users_card(records):
    response = create(records.owner)
    assert response.status_code == 201
    notification = Notification.objects.get()
    assert notification.user == records.owner
    assert notification.card == records.cards[0]


@pytest.mark.parametrize('field', ['user', 'user_id', 'card'])
def test_foreign_owner_or_card_is_rejected_without_saving(records, field):
    foreign_id = records.cards[1].pk if field == 'card' else records.other.pk
    response = create(records.owner, **{field: foreign_id})
    assert response.status_code == 400
    assert not Notification.objects.exists()


def test_invalid_payload_does_not_save(records):
    response = create(records.owner, title='')
    assert response.status_code == 400
    assert 'title' in response.data
    assert not Notification.objects.exists()


@pytest.mark.parametrize(
    'payload, expected',
    [
        ({'created_at': '2026-11-05T12:30:00Z'}, datetime(2026, 11, 5, 12, 30, tzinfo=UTC)),
        ({'date': '2026-11-05T09:30:00-03:00'}, datetime(2026, 11, 5, 12, 30, tzinfo=UTC)),
        (
            {'created_at': '2026-11-05 09:30:00'},
            timezone.make_aware(datetime(2026, 11, 5, 9, 30)),
        ),
        (
            {'created_at': '2026-11-05T12:30:00Z', 'date': '2020-01-01T00:00:00Z'},
            datetime(2026, 11, 5, 12, 30, tzinfo=UTC),
        ),
    ],
)
def test_client_timestamp_is_persisted_instead_of_auto_now_add(records, payload, expected):
    assert create(records.owner, **payload).status_code == 201
    assert Notification.objects.get().created_at == expected


def test_invalid_timestamp_falls_back_to_server_time(records):
    before = timezone.now()
    assert create(records.owner, created_at='invalid').status_code == 201
    assert before <= Notification.objects.get().created_at <= timezone.now()


def test_unsupported_four_byte_characters_are_sanitized(records):
    response = create(records.owner, title='Compra 🛒', message='Pagamento 💳 final 3456')
    assert response.status_code == 201
    notification = Notification.objects.get()
    assert '🛒' not in notification.title
    assert '💳' not in notification.message
    assert notification.card == records.cards[0]


def test_card_lookup_failure_preserves_the_notification(records, mocker):
    mocker.patch('api.views.notification.CardService.get_all', side_effect=RuntimeError('unavailable'))
    assert create(records.owner).status_code == 201
    notification = Notification.objects.get()
    assert notification.user == records.owner
    assert notification.card is None


def test_card_resolution_failure_preserves_the_notification_without_a_card(records, mocker):
    mocker.patch('api.views.notification.CardService.get_by_id', side_effect=RuntimeError('unavailable'))
    assert create(records.owner).status_code == 201
    notification = Notification.objects.get()
    assert notification.user == records.owner
    assert notification.card is None
