import pytest
from django.urls import reverse

from statement.models import Card, CardNumber


@pytest.fixture
def card_web(authenticated_web, ledger):
    ledger.user.is_staff = True
    ledger.user.save()
    authenticated_web.client.force_login(ledger.user)
    return authenticated_web.client


def payload(ledger, *, existing=True, **extra):
    return {
        'description': 'Cartão atualizado',
        'flag': ledger.card.flag_id,
        'limits': '1000',
        'account': ledger.account.pk,
        'closing_day': 3,
        'expiration_day': 10,
        'card_numbers-TOTAL_FORMS': 2,
        'card_numbers-INITIAL_FORMS': 1 if existing else 0,
        'card_numbers-MIN_NUM_FORMS': 0,
        'card_numbers-MAX_NUM_FORMS': 1000,
        'card_numbers-0-id': ledger.number.pk if existing else '',
        'card_numbers-0-number': '1234',
        'card_numbers-0-name': '',
        'card_numbers-0-home_screen': 'on',
        'card_numbers-1-home_screen': 'on',
        **extra,
    }


def test_card_creation_saves_the_owner_and_number_as_one_form(card_web, ledger):
    response = card_web.post(reverse('create_card'), payload(ledger, existing=False))
    assert response.status_code == 302
    card = Card.objects.get(description='Cartão atualizado')
    assert card.user == ledger.user
    assert card.card_numbers.get().number == '1234'


@pytest.mark.parametrize('invalid', ['card', 'number'])
def test_invalid_card_or_number_does_not_create_a_card(card_web, ledger, invalid):
    data = payload(ledger, existing=False)
    if invalid == 'card':
        data['description'] = ''
    else:
        data.update({'card_numbers-0-number': '', 'card_numbers-0-name': 'Número obrigatório'})
    before = Card.objects.count()
    response = card_web.post(reverse('create_card'), data)
    assert response.status_code == 200
    assert Card.objects.count() == before
    assert response.context['form'].errors or response.context['formset'].errors


def test_card_update_propagates_visibility_when_the_number_was_not_explicitly_changed(card_web, ledger):
    response = card_web.post(reverse('update_card', args=[ledger.card.pk]), payload(ledger))
    assert response.status_code == 302
    ledger.number.refresh_from_db()
    ledger.card.refresh_from_db()
    assert not ledger.number.home_screen
    assert ledger.card.description == 'Cartão atualizado'


def test_card_update_preserves_an_explicit_number_visibility_choice(card_web, ledger):
    data = payload(ledger, home_screen='on')
    data.pop('card_numbers-0-home_screen')
    assert card_web.post(reverse('update_card', args=[ledger.card.pk]), data).status_code == 302
    ledger.number.refresh_from_db()
    assert not ledger.number.home_screen


@pytest.mark.parametrize('invalid', ['card', 'number'])
def test_invalid_card_update_preserves_existing_records(card_web, ledger, invalid):
    data = payload(ledger)
    data['description' if invalid == 'card' else 'card_numbers-0-number'] = ''
    response = card_web.post(reverse('update_card', args=[ledger.card.pk]), data)
    assert response.status_code == 200
    ledger.card.refresh_from_db()
    assert ledger.card.description == 'Card'


def test_card_owner_edit_form_is_available_and_other_users_are_redirected(card_web, ledger):
    assert card_web.get(reverse('update_card', args=[ledger.card.pk])).status_code == 200
    ledger.user.is_staff = False
    ledger.user.save()
    assert card_web.get(reverse('update_card', args=[ledger.other_card.pk])).status_code == 302


def test_optional_visibility_propagation_failure_does_not_block_card_update(card_web, ledger, mocker):
    mocker.patch.object(CardNumber, 'save', side_effect=RuntimeError('optional propagation failed'))
    response = card_web.post(reverse('update_card', args=[ledger.card.pk]), payload(ledger))
    assert response.status_code == 302
    ledger.card.refresh_from_db()
    assert ledger.card.description == 'Cartão atualizado'
