from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.forms.models import model_to_dict
from django.http import Http404
from django.test import RequestFactory, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from api.serializers.transaction import TransactionSerializer
from api.views.account import AccountView
from api.views.category import CategoryView
from api.views.notification import NotificationView
from api.views.transaction import TransactionView
from login.forms.user_forms import UserForm
from login.models import User
from myfinance.environment import env_bool
from statement.authentication import DeviceTokenAuthentication
from statement.models import (
    Account, AccountType, Bank, Card, CardNumber, Category, Currency, Device,
    Dream, Flag, Installment, Notification, Subcategory, Transaction,
)
from statement.views.core.installment import InstallmentView
from statement.views.core.transaction import TransactionView as WebTransactionView


@pytest.fixture
def records(db):
    owner = User.objects.create(username='security-owner', email='owner@security.invalid')
    other = User.objects.create(username='security-other', email='other@security.invalid')
    bank = Bank.objects.create(description='Bank')
    kind = AccountType.objects.create(description='Account')
    accounts = [Account.objects.create(user=user, bank=bank, type=kind, number=f'private-{user.pk}')
                for user in (owner, other)]
    flag = Flag.objects.create(description='Flag')
    cards = [Card.objects.create(user=user, flag=flag, description=f'Card {user.pk}', closing_day=3,
                                 expiration_day=10) for user in (owner, other)]
    numbers = [CardNumber.objects.create(card=card, number=f'000{card.pk}', name=f'Number {card.pk}')
               for card in cards]
    category = Category.objects.create(description='Expense', type='saida')
    subcategory = Subcategory.objects.create(description='Test', category=category)
    Currency.objects.get_or_create(pk='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
    return SimpleNamespace(**locals())


def call(view, action, user, data=None, pk=None, method='post', url='/api/resource/'):
    request = getattr(APIRequestFactory(), method)(url, data=data, format='json')
    force_authenticate(request, user=user)
    return view.as_view({method: action})(request, **({'pk': pk} if pk is not None else {}))


def transaction_data(records, **extra):
    return {
        'description': 'Security test', 'value': 10, 'posted_date': '2026-11-05',
        'payment_date': '2026-11-05', 'type': 'saida', 'currency': 'BRL',
        'installments_number': 0, 'paid': 0,
        'category': records.category.pk, 'subcategory': records.subcategory.pk, **extra,
    }


@pytest.mark.parametrize('relation', ['account', 'card', 'card_number', 'dream', 'installment', 'source_notification'])
def test_api_rejects_foreign_transaction_relationship(records, relation):
    private = {
        'account': records.accounts[1], 'card': records.cards[1], 'card_number': records.numbers[1],
        'dream': Dream.objects.create(user=records.other, description='Foreign dream'),
        'installment': Installment.objects.create(user=records.other, description='Foreign plan', posted_date=date.today()),
        'source_notification': Notification.objects.create(user=records.other, app='bank', title='Private', message='Secret'),
    }
    response = call(TransactionView, 'create', records.owner, transaction_data(records, **{relation: private[relation].pk}))
    assert response.status_code in (400, 403, 404)
    assert not Transaction.objects.filter(user=records.owner).exists()


def test_owner_can_create_and_update_transaction(records):
    data = transaction_data(records, account=records.accounts[0].pk)
    response = call(TransactionView, 'create', records.owner, data)
    assert response.status_code == 201, response.data
    response = call(TransactionView, 'update', records.owner, {**data, 'description': 'Edited'},
                    pk=response.data['id'], method='put')
    assert response.status_code == 200, response.data
    assert Transaction.objects.get(pk=response.data['id']).description == 'Edited'


@pytest.mark.parametrize('field', ['user', 'user_id'])
def test_cannot_change_owner_through_api(records, field):
    instance = records.accounts[0]
    data = {**model_to_dict(instance), field: records.other.pk}
    response = call(AccountView, 'update', records.owner, data, instance.pk, method='put')
    assert response.status_code == 400
    instance.refresh_from_db()
    assert instance.user_id == records.owner.pk


def test_expansion_hides_foreign_legacy_relationships(records):
    dream = Dream.objects.create(user=records.other, description='Private dream')
    installment = Installment.objects.create(user=records.other, description='Private plan', posted_date=date.today())
    notification = Notification.objects.create(user=records.other, app='bank', title='Private', message='Secret')
    transaction = Transaction.objects.create(user=records.owner, account=records.accounts[1],
        card=records.cards[1], card_number=records.numbers[1], dream=dream,
        installment=installment, source_notification=notification, **{
            key: value for key, value in transaction_data(records).items()
            if key not in ('category', 'subcategory', 'currency')
        }, category=records.category, subcategory=records.subcategory, currency_id='BRL')
    request = SimpleNamespace(user=records.owner, query_params={'expand': 'account,card,card_number'})
    data = TransactionSerializer(transaction, context={'request': request}).data
    assert data['account'] is None
    assert data['card'] is None
    assert data['card_number'] is None
    assert data['dream'] is None
    assert data['installment'] is None
    assert data['source_notification'] is None


@pytest.mark.parametrize('relation', ['account', 'card', 'card_number', 'dream', 'installment', 'source_notification'])
def test_update_cannot_add_foreign_transaction_relationship(records, relation):
    data = transaction_data(records, account=records.accounts[0].pk)
    created = call(TransactionView, 'create', records.owner, data)
    assert created.status_code == 201
    private = {
        'account': records.accounts[1], 'card': records.cards[1], 'card_number': records.numbers[1],
        'dream': Dream.objects.create(user=records.other, description='Foreign dream'),
        'installment': Installment.objects.create(user=records.other, description='Foreign plan', posted_date=date.today()),
        'source_notification': Notification.objects.create(user=records.other, app='bank', title='Private', message='Secret'),
    }
    response = call(TransactionView, 'update', records.owner, {**data, relation: private[relation].pk},
                    pk=created.data['id'], method='put')
    assert response.status_code == 400
    instance = Transaction.objects.get(pk=created.data['id'])
    assert instance.account_id == records.accounts[0].pk
    assert instance.card_id is None
    assert instance.dream_id is None
    assert instance.installment_id is None
    assert instance.source_notification_id is None


def test_shared_card_read_does_not_expand_owner_account(records):
    records.numbers[1].visible_to.add(records.owner)
    transaction = Transaction.objects.create(user=records.other, account=records.accounts[1],
        card=records.cards[1], card_number=records.numbers[1], category=records.category,
        subcategory=records.subcategory, description='Shared', value=10,
        posted_date=date.today(), payment_date=date.today())
    request = SimpleNamespace(user=records.owner, query_params={'expand': 'account,card,card_number'})
    data = TransactionSerializer(transaction, context={'request': request}).data
    assert data['account'] is None
    assert data['card']['id'] == records.cards[1].pk
    assert 'account' not in data['card']
    assert data['card_number']['id'] == records.numbers[1].pk


def test_notification_patch_is_owner_scoped_and_validated(records):
    notification = Notification.objects.create(user=records.other, app='bank', title='Private', message='Secret')
    response = call(NotificationView, 'partial_update', records.owner, {'is_used': True}, notification.pk, method='patch')
    assert response.status_code == 404
    assert 'Secret' not in str(response.data)
    notification.refresh_from_db()
    assert not notification.is_used
    response = call(NotificationView, 'partial_update', records.other, {'is_used': True}, notification.pk, method='patch')
    assert response.status_code == 200, response.data
    notification.refresh_from_db()
    assert notification.is_used
    response = call(NotificationView, 'partial_update', records.other, {'card': records.cards[0].pk}, notification.pk, method='patch')
    assert response.status_code == 400


@pytest.mark.parametrize('action,method', [('create', 'post'), ('update', 'put'), ('destroy', 'delete')])
def test_global_writes_require_staff(records, action, method):
    target = Category.objects.create(description='Unreferenced', type='saida')
    with patch('statement.services.core.category.CategoryService.send_category_update'):
        response = call(CategoryView, action, records.owner, {'description': 'New', 'type': 'saida'},
                        pk=None if action == 'create' else target.pk, method=method)
        assert response.status_code in (401, 403)
        records.owner.is_staff = True
        response = call(CategoryView, action, records.owner, {'description': 'New', 'type': 'saida'},
                        pk=None if action == 'create' else target.pk, method=method)
        assert response.status_code in (200, 201, 204), response.data


def test_inactive_device_user_is_rejected(records):
    device = Device.objects.create(user=records.owner, name='Test')
    records.owner.is_active = False
    records.owner.save(update_fields=['is_active'])
    request = APIRequestFactory().get('/api/accounts/', HTTP_AUTHORIZATION=f'Bearer {device.token}')
    from rest_framework.permissions import IsAuthenticated
    response = AccountView.as_view({'get': 'list'}, authentication_classes=[DeviceTokenAuthentication],
                                   permission_classes=[IsAuthenticated])(request)
    assert response.status_code in (401, 403)


def test_foreign_installment_cannot_reach_form_or_render(records):
    installment = Installment.objects.create(user=records.other, description='Secret', posted_date=date.today())
    request = RequestFactory().get('/edit/')
    request.user = records.owner
    view = InstallmentView()
    with patch.object(view, '_render') as render:
        with pytest.raises(Http404):
            view.update(request, installment.pk)
        render.assert_not_called()


def test_card_context_contains_only_visible_numbers(records):
    request = RequestFactory().get('/record/')
    request.user = records.owner
    context = WebTransactionView()._add_context_on_templatetags(request, None)
    assert [item['id'] for item in context['card_numbers_json']] == [records.numbers[0].pk]
    records.numbers[1].visible_to.add(records.owner)
    context = WebTransactionView()._add_context_on_templatetags(request, None)
    assert {item['id'] for item in context['card_numbers_json']} == {item.pk for item in records.numbers}


@pytest.mark.parametrize('value,expected', [('false', False), ('0', False), ('False', False),
                                         ('true', True), ('1', True), ('yes', True)])
def test_environment_boolean(monkeypatch, value, expected):
    monkeypatch.setenv('DEBUG', value)
    assert env_bool('DEBUG') is expected


@override_settings(AUTH_PASSWORD_VALIDATORS=[
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
])
@pytest.mark.parametrize('password,valid', [('1', False), ('security-person', False), ('Valid!unrelated-4Z-pine', True)])
def test_registration_password_policy(db, password, valid):
    form = UserForm({'username': 'security-person', 'name': 'Security Person', 'email': 'person@security.invalid',
                     'password1': password, 'password2': password})
    assert form.is_valid() is valid
