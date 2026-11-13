from statement.services.core.account import AccountService
from statement.services.core.card import CardService


def sidebar_navigation(request):
    """Populate the sidebar on every authenticated page, including profile pages."""
    if not request.user.is_authenticated:
        return {}

    user = request.user
    invoices = list(CardService.get_all(user))
    owned_ids = {card.id for card in invoices}
    dependent_cards = CardService.model.objects.filter(card_numbers__dependente=user).distinct()
    invoices.extend(card for card in dependent_cards if card.id not in owned_ids)
    return {
        'extracts': AccountService.get_all(user),
        'invoices': invoices,
    }
