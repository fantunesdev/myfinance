from statement.models import Card


def create_card(card):
    new_card = Card.objects.create(
        flag=card.flag,
        icon=card.icon,
        description=card.description,
        limits=card.limits,
        account=card.account,
        expiration_day=card.expiration_day,
        closing_day=card.closing_day,
        home_screen=card.home_screen,
        user=card.user,
    )
    return new_card


def get_cards(user):
    return Card.objects.filter(user=user)


def get_card_by_id(id, user):
    return Card.objects.get(id=id, user=user)


def update_card(old_card, new_card):
    old_card.flag = new_card.flag
    old_card.icon = new_card.icon
    old_card.description = new_card.description
    old_card.limits = new_card.limits
    old_card.account = new_card.account
    old_card.expiration_day = new_card.expiration_day
    old_card.closing_day = new_card.closing_day
    old_card.home_screen = new_card.home_screen
    old_card.user = new_card.user
    old_card.save(force_update=True)
    return old_card


def delete_card(card):
    card.delete()
