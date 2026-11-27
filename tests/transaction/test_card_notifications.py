from types import SimpleNamespace

import pytest

from statement.services.core.card import CardService


def card(*numbers, app='bank.app', user_id=1, card_id=10):
    return SimpleNamespace(
        id=card_id,
        user=SimpleNamespace(id=user_id),
        account=SimpleNamespace(bank=SimpleNamespace(app_id=app)),
        card_numbers=SimpleNamespace(
            all=lambda: [SimpleNamespace(id=index + 1, number=number) for index, number in enumerate(numbers)]
        ),
    )


def notification(message='Compra final 3456', app='bank.app', user_id=1):
    return SimpleNamespace(
        id=20,
        message=message,
        app=app,
        user_id=user_id,
        user=SimpleNamespace(id=user_id) if user_id is not None else None,
    )


@pytest.mark.parametrize(
    'numbers, message, app, user_id, expected',
    [
        (['1234 5678 9012 3456'], 'Compra FINAL 3456', 'bank.app', 1, True),
        (['1234 5678 9012 3456'], 'Compra final 9999', 'bank.app', 1, False),
        (['1234 5678 9012 3456'], 'Compra final 3456', 'other.app', 1, False),
        (['1234 5678 9012 3456'], 'Compra final 3456', 'bank.app', 2, False),
        ([], 'Compra final 3456', 'bank.app', 1, True),
        ([], 'Compra final 3456', 'bank.app', None, False),
        (['1234 5678 9012 3456'], 'Compra final 3456', 'bank.app', None, True),
        (['1234 5678 9012 3456'], None, 'bank.app', 1, True),
        ([None], 'Compra final 3456', 'bank.app', 1, False),
        (['1111', '3456'], 'Compra final 3456', 'bank.app', 1, True),
    ],
)
def test_notification_matching_respects_bank_owner_and_card_number(numbers, message, app, user_id, expected):
    assert CardService.is_notification_owner(card(*numbers), notification(message, app, user_id)) is expected


def test_binding_records_the_matching_card_and_number():
    first = card('1111', '3456')
    second = card('9999', card_id=11)
    item = notification()
    result = CardService.are_notifications_owner([first, second], [item])
    assert result == {item.id: [first]}
    assert item.card == first
    assert item.card_id == first.id
    assert item.card_number.number == '3456'
    assert item.card_number_id == 2


def test_nonmatching_notification_has_no_card_or_number():
    item = notification(user_id=2)
    assert CardService.are_notifications_owner([card('3456')], [item]) == {item.id: []}
    assert item.card_id is None
    assert item.card_number is None
    assert item.card_number_id is None


def test_broken_card_does_not_prevent_matching_other_cards():
    broken = card()
    broken.account = None
    valid = card('3456')
    item = notification()
    assert CardService.are_notifications_owner([broken, valid], [item]) == {item.id: [valid]}
    assert item.card_id == valid.id
