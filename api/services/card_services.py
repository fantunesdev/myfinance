from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from statement.services import card_services


def get_cards(user):
    cards = card_services.get_cards(user)
    if cards:
        return cards
    raise Http404


def get_card_by_id(card_id, user):
    try:
        return card_services.get_card_by_id(card_id, user)
    except ObjectDoesNotExist:
        raise Http404
