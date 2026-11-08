from datetime import date
from types import SimpleNamespace

import pytest
from django.db.models import Sum

from login.models import User
from statement.models import Card, CardNumber, Category, Currency, Flag, Subcategory, Transaction
from statement.views.core.invoice import InvoiceView


@pytest.mark.django_db
@pytest.mark.parametrize('viewer_role', ['owner', 'dependent'])
@pytest.mark.parametrize('current_month', [False, True])
def test_invoice_shared_numbers_do_not_duplicate_transactions(mocker, viewer_role, current_month):
    owner, dependent, other = [User.objects.create(username=name, email=f'{name}@test.invalid') for name in ('owner', 'dependent', 'other')]
    card = Card.objects.create(
        user=owner, description='Cartão', flag=Flag.objects.create(description='Bandeira'),
        expiration_day=10, closing_day=3,
    )
    own_number = CardNumber.objects.create(card=card, number='1111', dependente=dependent)
    own_number.visible_to.add(owner, other)
    shared_number = CardNumber.objects.create(card=card, number='2222', dependente=other)
    shared_number.visible_to.add(dependent, owner)
    hidden_number = CardNumber.objects.create(card=card, number='3333', dependente=other)
    category = Category.objects.create(description='Compras')
    subcategory = Subcategory.objects.create(category=category, description='Geral')
    currency = Currency.objects.create(id='BRL', description='Real', symbol='R$')

    def create_transaction(number, value, month=11, direct_card=True):
        return Transaction.objects.create(
            user=owner, card=card if direct_card else None, card_number=number,
            posted_date=date(2026, month, 1), payment_date=date(2026, month, 10),
            category=category, subcategory=subcategory, currency=currency,
            description='Compra', value=value,
        )

    own = create_transaction(own_number, 100)
    same_value = create_transaction(own_number, 100, direct_card=False)
    shared = create_transaction(shared_number, 50)
    hidden = create_transaction(hidden_number, 25)
    parent = create_transaction(None, 10)
    create_transaction(own_number, 900, month=10)
    viewer = owner if viewer_role == 'owner' else dependent
    view = InvoiceView()
    mocker.patch.object(view, '_render', side_effect=lambda request, form, template, context: context)
    mocker.patch.object(view, 'set_navigation_templatetags', return_value={})
    mocker.patch.object(view, '_get_current_month', return_value=(2026, 11))
    request = SimpleNamespace(user=viewer)
    if current_month:
        context = view.get_current_month(request, card.pk)
    else:
        context = view.get_by_year_and_month(request, card.pk, 2026, 11)

    expected = [own.pk, same_value.pk, shared.pk]
    if viewer_role == 'owner':
        expected += [hidden.pk, parent.pk]
    assert sorted(context['instances'].values_list('pk', flat=True)) == sorted(expected)
    groups = context['grouped_instances']
    assert sorted(tx.pk for group in groups for tx in group['transactions']) == sorted(expected)
    totals = {group['card_number'].pk if group['card_number'] else None: group['total'] for group in groups}
    assert totals[own_number.pk] == 200
    assert totals[shared_number.pk] == 50
    total = 285 if viewer_role == 'owner' else 250
    assert sum(totals.values()) == total
    assert context['instances'].aggregate(total=Sum('value'))['total'] == total
    assert context['dashboard']['expenses'] == total
