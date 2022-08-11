from django.http import Http404

from balanco.services import cartao_service


def get_cards(user):
    cards = cartao_service.listar_cartoes(user)
    if cards:
        return cards
    raise Http404


def get_card_id(card_id, user):
    card = cartao_service.listar_cartao_id(card_id, user)
    if card:
        return card
    raise Http404
