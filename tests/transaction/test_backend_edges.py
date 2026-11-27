import builtins
import runpy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.forms import modelform_factory
from django.test import override_settings

from api.apps import ApiConfig
from api.services.websocket_services import send_websocket_update
from investments import events
from login.admin_apps import SecurityAdminConfig
from statement.access import visible_card_numbers, visible_cards
from statement.forms.core.transaction import TransactionForm
from statement.models import Notification, NotificationTitle
from statement.services.core.account import AccountService
from statement.services.core.notification_title import NotificationTitleService
from statement.services.core.transaction import TransactionService
from statement.utils.datetime import DateTimeUtils
from statement.utils.jwt import JWTUtils
from statement.utils.notes_html import formatted_notes
from statement.utils.transaction_input import parse_amount
from statement.utils.transaction_provenance import validate_notification_source


def test_app_configuration_and_legacy_url_modules_remain_loadable():
    from statement.urls import next_month_view_url
    from statement.urls.core import account_type

    assert ApiConfig.name == 'api'
    assert SecurityAdminConfig.default_site == 'login.admin_site.SecurityAdminSite'
    assert account_type.urlpatterns and next_month_view_url.urlpatterns


@pytest.mark.parametrize('name', ['statement', 'investments'])
def test_optional_signal_import_failure_does_not_abort_app_initialization(mocker, name):
    original = builtins.__import__

    def importing(module, *args, **kwargs):
        if module == f'{name}.signals':
            raise ImportError('optional signals unavailable')
        return original(module, *args, **kwargs)

    mocker.patch('builtins.__import__', side_effect=importing)
    apps.get_app_config(name).ready()


def test_development_urls_serve_media_only_when_debug_is_enabled(authenticated_web):
    root = Path(__file__).resolve().parents[2]
    with override_settings(DEBUG=True, MEDIA_URL='/media/'):
        paths = runpy.run_path(str(root / 'myfinance/urls.py'))['urlpatterns']
    assert any('media/' in str(path.pattern) for path in paths)


def test_anonymous_users_cannot_see_cards(ledger):
    for user in (None, AnonymousUser()):
        assert not visible_card_numbers(user).exists()
        assert not visible_cards(user).exists()


def test_notification_titles_ignore_empty_values_and_create_missing_titles(ledger):
    assert NotificationTitleService.ensure_titles(['', 'Compra'])[0].title == 'Compra'
    assert NotificationTitle.objects.count() == 1


def test_field_patch_rejects_invalid_data_and_unknown_model_fields(ledger):
    with pytest.raises(ValueError, match='dicionário'):
        AccountService.patch(ledger.account, [])
    with pytest.raises(ValueError, match='não existe'):
        AccountService.patch(ledger.account, {'unknown': 'value'})


def test_model_can_be_converted_back_to_an_unbound_prefilled_form(ledger):
    Form = modelform_factory(ledger.account.__class__, exclude=['user'])
    form = AccountService.instance_to_form(ledger.account, Form)
    assert form.data['bank'] == ledger.account.bank_id


@pytest.mark.parametrize('relation', ['card', 'number', 'account'])
def test_visibility_recalculation_updates_existing_transactions(ledger, entry, relation):
    if relation == 'account':
        item = entry(home_screen=False)
        TransactionService.recalculate_home_screen_for_account(ledger.account.pk)
    else:
        item = entry(
            account=None,
            card=ledger.card,
            card_number=ledger.number if relation == 'number' else None,
            home_screen=False,
        )
        if relation == 'number':
            TransactionService.recalculate_home_screen_for_card_number(ledger.number.pk)
        else:
            ledger.card.home_screen = True
            ledger.card.save()
            TransactionService.recalculate_home_screen_for_card(ledger.card.pk)
    item.refresh_from_db()
    assert item.home_screen


def test_legacy_notification_provenance_uses_its_cards_owner(ledger):
    notification = Notification.objects.create(
        card=ledger.card, app='bank.app', title='Compra', message='Compra de R$ 25,00 em Loja.'
    )
    instance = SimpleNamespace(event_type='', source_notification=notification, merchant_description='')
    validate_notification_source(instance, ledger.user)
    assert instance.source_type == 'notification'
    assert instance.merchant_description == 'Loja'
    with pytest.raises(ValidationError):
        validate_notification_source(instance, ledger.other)


def test_invalid_card_number_relationship_is_rejected_even_with_a_broad_queryset(ledger):
    form = TransactionForm(
        ledger.user,
        {
            'description': 'Compra',
            'value': 10,
            'type': 'saida',
            'currency': 'BRL',
            'category': ledger.category.pk,
            'subcategory': ledger.subcategory.pk,
            'card': ledger.card.pk,
            'card_number': ledger.number.pk,
            'posted_date': '2026-11-05',
            'payment_date': '2026-12-10',
            'installments_number': 0,
            'paid': 0,
        },
    )
    ledger.number.card = ledger.other_card
    ledger.number.save()
    form.fields['card_number'].queryset = ledger.number.__class__.objects.all()
    assert not form.is_valid()
    assert 'card_number' in form.errors


def test_datetime_month_arithmetic_preserves_the_time_of_day():
    assert DateTimeUtils.add_months(datetime(2026, 12, 31, 12, 30), 2) == datetime(2027, 2, 28, 12, 30)


@pytest.mark.parametrize('value, expected', [(None, None), ('invalid', None), ('1.000.000', 1000000), ('NaN', None)])
def test_amount_parser_rejects_invalid_financial_values(value, expected):
    assert parse_amount(value) == expected


def test_formatted_notes_handle_self_closing_tags_and_strip_script_content():
    rendered = str(formatted_notes('<script>secret<br/></script><p/>Texto<br/>'))
    assert 'secret' not in rendered
    assert 'Texto' in rendered
    assert '<br>' in rendered or '<br/>' in rendered


def test_legacy_jwt_generation_uses_configured_algorithm_and_expiration(ledger, mocker, settings):
    from jose import jwt

    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 15
    settings.ALGORITHM = 'HS256'
    mocker.patch('statement.utils.jwt.CLIENT_SECRET', 'test-secret-' * 4)
    token = JWTUtils.generate_token(ledger.user)
    assert jwt.decode(token, 'test-secret-' * 4, algorithms=['HS256'])['user_id'] == ledger.user.pk
    with pytest.raises(ValueError):
        JWTUtils.generate_access_token_for_user(object())


@pytest.mark.parametrize('failure', ['read', 'write', 'channel'])
def test_investment_cache_or_channel_outage_does_not_break_committed_operations(ledger, mocker, failure):
    if failure == 'read':
        mocker.patch('investments.events.cache.add', side_effect=RuntimeError('offline'))
        assert events.dashboard_revision(ledger.user.pk) is None
    elif failure == 'write':
        mocker.patch('investments.events.cache.set', side_effect=RuntimeError('offline'))
        events.publish_changes([ledger.user.pk])
    else:
        mocker.patch('investments.events.get_channel_layer', side_effect=RuntimeError('offline'))
        events.publish_changes([ledger.user.pk])
    events.mark_changed(None)


def test_websocket_update_contract_serializes_known_entities_and_rejects_unknown_ones(ledger, mocker):
    layer = mocker.Mock(group_send=mocker.AsyncMock())
    mocker.patch('api.services.websocket_services.get_channel_layer', return_value=layer)
    send_websocket_update('categories', ledger.category.__class__.objects.all())
    assert layer.group_send.call_args.args[1]['data']['categories'][0]['id'] == ledger.category.pk
    with pytest.raises(ValueError, match='Serializer'):
        send_websocket_update('unknown', {})
