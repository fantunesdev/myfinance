"""Explicit read visibility and owner-only relationships for financial writes."""
from django.db.models import Q

from statement.models import Card, CardNumber


def visible_card_numbers(user):
    if not user or not user.is_authenticated:
        return CardNumber.objects.none()
    return CardNumber.objects.filter(
        Q(card__user=user) | Q(dependente=user) | Q(visible_to=user)
    ).distinct()


def visible_cards(user):
    if not user or not user.is_authenticated:
        return Card.objects.none()
    return Card.objects.filter(
        Q(user=user) | Q(card_numbers__in=visible_card_numbers(user))
    ).distinct()


def restrict_write_relations(form, user):
    """Global taxonomy stays global; private foreign keys must be owned."""
    for field in form.fields.values():
        queryset = getattr(field, 'queryset', None)
        if queryset is None:
            continue
        model = queryset.model
        if model is CardNumber:
            field.queryset = queryset.filter(card__user=user)
        elif any(item.name == 'user' for item in model._meta.fields):
            field.queryset = queryset.filter(user=user)
    return form
