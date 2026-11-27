import json
from datetime import date

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from api.views.transaction import TransactionView
from statement.models import Category, Installment, Subcategory, Transaction


def call(user, action='create', data=None, method='post', **kwargs):
    request = getattr(APIRequestFactory(), method)('/api/transactions/', data or {}, format='json')
    force_authenticate(request, user=user)
    return TransactionView.as_view({method: action})(request, **kwargs)


def test_creation_rejects_an_explicit_foreign_owner(ledger, transaction_payload):
    response = call(ledger.user, data=transaction_payload(user=ledger.other.pk))
    assert response.status_code == 400
    assert not Transaction.objects.exists()


def test_opted_in_fixed_expense_is_ignored_on_api_import(ledger, entry, transaction_payload):
    existing = entry(fixed=True, event_type='fixed_expense', source_type='csv', original_description='Mercado')
    response = call(
        ledger.user, data=transaction_payload(source_type='csv', event_type='purchase', original_description='Mercado')
    )
    assert response.status_code == 200
    assert response.data['ignored']
    assert response.data['fixed_transaction_id'] == existing.pk
    assert Transaction.objects.count() == 1


def test_installment_duplicates_are_disambiguated_by_original_source_description(ledger, entry, transaction_payload):
    existing = entry(paid=1, installments_number=3, original_description='Loja A')
    entry(paid=1, installments_number=3, original_description='Loja B')
    response = call(
        ledger.user,
        data=transaction_payload(
            description='Mercado 1/3', original_description='Loja A', matching_fields=['original_description']
        ),
    )
    assert response.status_code == 200
    assert response.data['duplicate_id'] == existing.pk


def test_ambiguous_installments_with_an_unknown_match_rule_are_not_discarded(ledger, entry, transaction_payload):
    entry(paid=1, installments_number=3)
    entry(paid=1, installments_number=3)
    response = call(ledger.user, data=transaction_payload(description='Mercado 1/3', matching_fields=['unknown']))
    assert response.status_code == 201
    assert Transaction.objects.count() == 5


def test_card_duplicate_detection_includes_the_specific_card_number(ledger, entry, transaction_payload):
    existing = entry(account=None, card=ledger.card, card_number=ledger.number)
    response = call(
        ledger.user,
        data=transaction_payload(
            account='',
            card=ledger.card.pk,
            card_number=ledger.number.pk,
            matching_fields=['card', 'card_number', 'value'],
        ),
    )
    assert response.status_code == 200
    assert response.data['duplicate_id'] == existing.pk


@pytest.mark.parametrize('changes', [{'posted_date': ''}, {'value': 'invalid'}])
def test_first_installment_with_missing_date_or_invalid_value_returns_form_errors(ledger, transaction_payload, changes):
    response = call(ledger.user, data=transaction_payload(description='Mercado 1/3', **changes))
    assert response.status_code == 400
    assert not Transaction.objects.exists()


@pytest.mark.parametrize('date_field, value', [('posted_date', '2026-11-05'), ('date', '2026-11-05 12:30:00')])
def test_account_creation_normalizes_dates_and_derives_payment_date(ledger, transaction_payload, date_field, value):
    payload = transaction_payload()
    payload.pop('posted_date')
    payload[date_field] = value
    response = call(ledger.user, data=payload)
    assert response.status_code == 201
    transaction = Transaction.objects.get()
    assert transaction.user == ledger.user
    assert transaction.posted_date == transaction.payment_date == date(2026, 11, 5)
    assert transaction.home_screen
    assert transaction.value == 25


@pytest.mark.parametrize('prepaid, expected', [(False, date(2026, 12, 10)), (True, date(2026, 11, 5))])
def test_card_creation_uses_the_correct_invoice_date(ledger, transaction_payload, prepaid, expected):
    ledger.card.prepaid = prepaid
    ledger.card.save()
    response = call(
        ledger.user, data=transaction_payload(account='', card=ledger.card.pk, card_number=str(ledger.number.pk))
    )
    assert response.status_code == 201
    transaction = Transaction.objects.get()
    assert transaction.payment_date == expected
    assert transaction.card_number == ledger.number
    assert transaction.card == ledger.card


@pytest.mark.parametrize(
    'fields',
    [
        ['posted_date', 'description', 'value'],
        json.dumps(['posted_date', 'original_description', 'value']),
        'posted_date,description,value,account,category,subcategory,type',
    ],
)
def test_duplicate_import_returns_existing_record_without_creating_another(ledger, entry, transaction_payload, fields):
    existing = entry()
    response = call(ledger.user, data=transaction_payload(matching_fields=fields))
    assert response.status_code == 200
    assert response.data['duplicate_id'] == existing.pk
    assert Transaction.objects.count() == 1


def test_duplicate_matching_never_uses_another_users_transaction(ledger, entry, transaction_payload):
    entry(user=ledger.other, account=ledger.other_account)
    response = call(ledger.user, data=transaction_payload(matching_fields=['description', 'value', 'posted_date']))
    assert response.status_code == 201
    assert Transaction.objects.filter(user=ledger.user).count() == 1


@pytest.mark.parametrize('field', ['description', 'original_description', 'value', 'posted_date'])
def test_different_duplicate_key_allows_a_legitimate_purchase(ledger, entry, transaction_payload, field):
    existing = {
        'description': 'Outra loja',
        'original_description': 'OUTRO ORIGINAL',
        'value': 99,
        'posted_date': date(2026, 11, 6),
    }
    entry(**{field: existing[field]})
    response = call(ledger.user, data=transaction_payload(matching_fields=[field]))
    assert response.status_code == 201
    assert Transaction.objects.count() == 2


@pytest.mark.parametrize(
    'overrides',
    [
        {'posted_date': 'invalid'},
        {'category': 'missing'},
        {'card_number': 'invalid'},
        {'account': 999999},
        {'value': 'invalid'},
    ],
)
def test_invalid_creation_returns_validation_error_and_does_not_save(ledger, transaction_payload, overrides):
    response = call(ledger.user, data=transaction_payload(**overrides))
    assert response.status_code == 400
    assert not Transaction.objects.exists()


@pytest.mark.parametrize('mode, value', [('per_installment', '25'), ('total', '75')])
def test_first_installment_creates_the_whole_plan_with_correct_amounts(ledger, transaction_payload, mode, value):
    response = call(
        ledger.user,
        data=transaction_payload(
            account='',
            card=ledger.card.pk,
            description='Mercado Parcela 1/3',
            value=value,
            installment_value_mode=mode,
        ),
    )
    assert response.status_code == 201
    plan = Installment.objects.get()
    rows = list(Transaction.objects.order_by('paid'))
    assert len(rows) == 3
    assert [row.paid for row in rows] == [1, 2, 3]
    assert all(row.installment == plan and row.value == 25 and row.description == 'Mercado' for row in rows)
    assert [row.payment_date for row in rows] == [date(2026, 12, 10), date(2027, 1, 10), date(2027, 2, 10)]


def test_later_installment_is_ignored_without_creating_another_plan(ledger, transaction_payload):
    response = call(ledger.user, data=transaction_payload(description='Mercado', installment_text='2/3'))
    assert response.status_code == 200
    assert not Transaction.objects.exists()
    assert not Installment.objects.exists()


def test_reimported_first_installment_does_not_duplicate_the_plan(ledger, transaction_payload):
    payload = transaction_payload(account='', card=ledger.card.pk, description='Mercado 1/3')
    assert call(ledger.user, data=payload).status_code == 201
    response = call(ledger.user, data=payload)
    assert response.status_code == 200
    assert response.data['duplicate']
    assert Transaction.objects.count() == 3
    assert Installment.objects.count() == 1


def test_invalid_first_installment_returns_form_errors_without_creating_a_plan(ledger, transaction_payload):
    wrong_category = Category.objects.create(description='Outra categoria', type='saida')
    wrong_subcategory = Subcategory.objects.create(category=wrong_category, description='Outra')
    response = call(ledger.user, data=transaction_payload(description='Compra 1/3', subcategory=wrong_subcategory.pk))
    assert response.status_code == 400
    assert 'subcategory' in response.data
    assert not Transaction.objects.exists()
    assert not Installment.objects.exists()


@pytest.mark.parametrize(
    'action, kwargs',
    [
        ('list', {}),
        ('get_by_year', {'year': 2026}),
        ('get_by_year_and_month', {'year': 2026, 'month': 11}),
        ('get_extract_by_year_and_month', {'account_id': 'account', 'year': 2026, 'month': 11}),
        ('get_invoice_by_year_and_month', {'card_id': 'card', 'year': 2026, 'month': 11}),
    ],
)
def test_read_actions_filter_dates_and_user(ledger, entry, action, kwargs):
    account = ledger.account if 'account_id' in kwargs else None
    card = ledger.card if 'card_id' in kwargs else None
    current = entry(account=account, card=card)
    older = entry(account=account, card=card, payment_date=date(2025, 11, 5))
    entry(user=ledger.other, account=ledger.other_account)
    kwargs = {
        key: getattr(ledger, value).pk if value in ('account', 'card') else value for key, value in kwargs.items()
    }
    response = call(ledger.user, action, method='get', **kwargs)
    assert response.status_code == 200
    assert {row['id'] for row in response.data} == ({current.pk, older.pk} if action == 'list' else {current.pk})


@pytest.mark.parametrize('home_screen', ['true', '1', 'yes', 'TRUE'])
def test_dashboard_filter_omits_hidden_transactions(ledger, entry, home_screen):
    visible = entry(home_screen=True)
    entry(home_screen=False)
    response = call(
        ledger.user, 'get_by_year_and_month', {'home_screen': home_screen}, method='get', year=2026, month=11
    )
    assert response.status_code == 200
    assert [row['id'] for row in response.data] == [visible.pk]


@pytest.mark.parametrize(
    'relation, action',
    [
        ('other_account', 'get_extract_by_year_and_month'),
        ('other_card', 'get_invoice_by_year_and_month'),
    ],
)
def test_extract_and_invoice_reject_foreign_resources(ledger, relation, action):
    key = 'account_id' if relation == 'other_account' else 'card_id'
    response = call(ledger.user, action, method='get', year=2026, month=11, **{key: getattr(ledger, relation).pk})
    assert response.status_code == 404


def test_empty_period_returns_not_found(ledger):
    response = call(ledger.user, 'get_by_year_and_month', method='get', year=2026, month=11)
    assert response.status_code == 404


def test_list_expands_requested_relationships(ledger, entry):
    row = entry()
    response = call(ledger.user, 'list', {'expand': 'account,category,subcategory'}, method='get')
    assert response.status_code == 200
    assert response.data[0]['id'] == row.pk
    assert response.data[0]['account']['bank']['id'] == ledger.account.bank_id
    assert response.data[0]['category']['id'] == ledger.category.pk
    assert response.data[0]['subcategory']['id'] == ledger.subcategory.pk
