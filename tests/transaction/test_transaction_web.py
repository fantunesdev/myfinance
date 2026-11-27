from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from statement.models import AppConfig, Notification, NotificationTitle, NotificationTitlePreference, Transaction
from statement.services.core.installment import InstallmentService


@pytest.fixture
def browser(authenticated_web, ledger):
    authenticated_web.client.force_login(ledger.user)
    return authenticated_web.client


def web_payload(ledger, **overrides):
    return {
        'description': 'Mercado',
        'value': '30',
        'posted_date': '2026-11-05',
        'payment_date': '2026-11-05',
        'category': ledger.category.pk,
        'subcategory': ledger.subcategory.pk,
        'account': ledger.account.pk,
        'currency': 'BRL',
        'installments_number': 0,
        'paid': 0,
        'payment_method': 2,
        **overrides,
    }


def test_transaction_create_update_detail_and_delete(browser, ledger):
    response = browser.post(reverse('create_transaction', args=['saida']), web_payload(ledger))
    assert response.status_code == 302
    item = Transaction.objects.get()
    assert browser.get(reverse('detail_transaction', args=[item.pk])).status_code == 200
    payload = web_payload(ledger, type='saida', description='Updated', installment_option='editar')
    response = browser.post(reverse('update_transaction', args=[item.pk]), payload)
    assert response.status_code == 302
    item.refresh_from_db()
    assert item.description == 'Updated'
    assert browser.post(reverse('delete_transaction', args=[item.pk])).status_code == 302
    assert not Transaction.objects.exists()


def test_transaction_create_keeps_domain_errors_on_the_form(browser, ledger, mocker):
    mocker.patch('statement.views.core.transaction.TransactionService.create', side_effect=ValidationError('Rejected'))
    response = browser.post(reverse('create_transaction', args=['saida']), web_payload(ledger))
    assert response.status_code == 200
    assert 'Rejected' in response.context['form'].non_field_errors()
    assert not Transaction.objects.exists()


def test_transaction_annual_and_description_filters(browser, ledger, entry):
    own = entry(home_screen=True)
    entry(user=ledger.other, account=ledger.other_account, home_screen=True)
    response = browser.get(reverse('get_transactions_by_year', args=[2026]))
    assert response.status_code == 200
    assert [item.pk for item in response.context['instances']] == [own.pk]
    response = browser.get(reverse('get_transactions_by_description', args=['Mercado']))
    assert response.status_code == 200
    assert [item.pk for item in response.context['instances']] == [own.pk]


def test_account_extract_filters_account_and_period(browser, ledger, entry):
    own = entry()
    entry(account=None, card=ledger.card)
    response = browser.get(reverse('get_extract_by_account_year_and_month', args=[ledger.account.pk, 2026, 11]))
    assert response.status_code == 200
    assert [item.pk for item in response.context['instances']] == [own.pk]
    assert browser.get(reverse('get_current_month_extract_by_account', args=[ledger.account.pk])).status_code == 200


@pytest.mark.parametrize('source', ['pluggy', 'notifications', 'file', 'invalid'])
def test_import_page_selects_known_sources_and_preserves_card_context(browser, ledger, source):
    response = browser.get(reverse('import_transactions'), {'fonte': source})
    assert response.status_code == 200
    assert response.context['import_source'] == ('pluggy' if source == 'invalid' else source)
    assert response.context['card_numbers_json'][0]['id'] == ledger.number.pk


@pytest.mark.parametrize('classifier', ['enabled', 'disabled', 'offline'])
def test_import_page_converts_owned_enabled_notifications_without_creating_transactions(
    browser, ledger, mocker, classifier
):
    AppConfig.objects.create(enable_transaction_classifier=classifier != 'disabled')
    title = NotificationTitle.objects.create(title='Compra')
    NotificationTitlePreference.objects.create(user=ledger.user, title=title, enabled=True)
    item = Notification.objects.create(
        user=ledger.user,
        app='bank.app',
        title='Compra no crédito',
        message='Compra de R$ 25,00 em Loja. Cartão final 1234',
    )
    client = mocker.patch('statement.views.core.transaction.TransactionClassifierClient')
    if classifier == 'offline':
        client.return_value.predict.side_effect = RuntimeError('offline')
    else:
        client.return_value.predict.return_value = {
            'description': 'Loja',
            'category_id': ledger.category.pk,
            'subcategory_id': ledger.subcategory.pk,
        }
    response = browser.get(reverse('import_transactions'), {'fonte': 'notifications'})
    assert response.status_code == 200
    rows = response.context['notifications_json']
    assert len(rows) == 1
    assert rows[0]['notification_id'] == item.pk
    assert rows[0]['card_number_id'] == ledger.number.pk
    assert rows[0]['value'] == 25
    assert not Transaction.objects.exists()
    item.refresh_from_db()
    assert item.card == ledger.card


def test_import_page_can_render_legacy_titles_if_preferences_are_unavailable(browser, ledger, mocker):
    Notification.objects.create(
        user=ledger.user,
        card=ledger.card,
        app='bank.app',
        title='Legacy',
        message='Compra de R$ 25,00 em Loja. Cartão final 1234',
    )
    mocker.patch(
        'statement.services.core.notification_title.NotificationTitleService.get_enabled_titles_for_user',
        side_effect=RuntimeError('unavailable'),
    )
    response = browser.get(reverse('import_transactions'))
    assert response.status_code == 200
    assert len(response.context['notifications_json']) == 1


@pytest.mark.parametrize(
    'route, payload, valid',
    [
        ('update_next_month_view', {'day': 20, 'active': 'on'}, True),
        ('update_next_month_view', {'day': 40}, False),
        ('update_fuel_tracking', {'active': 'on'}, False),
        ('update_fuel_tracking', {}, True),
    ],
)
def test_profile_financial_preferences_validate_before_saving(browser, ledger, route, payload, valid):
    response = browser.post(reverse(route), payload)
    assert response.status_code == (302 if valid else 200)


def test_installment_plan_can_be_deleted_from_its_confirmation_page(browser, ledger, entry):
    first = entry(account=None, card=ledger.card, value=75, installments_number=3)
    plan = InstallmentService.create(None, user=ledger.user, transaction=first)
    response = browser.get(reverse('delete_installment', args=[plan.pk]))
    assert response.status_code == 200
    assert browser.post(reverse('delete_installment', args=[plan.pk])).status_code == 302
    assert not Transaction.objects.filter(installment_id=plan.pk).exists()


@pytest.mark.parametrize('new_count', [2, 3, 4])
def test_installment_plan_changes_keep_the_requested_number_of_rows(browser, ledger, entry, new_count):
    first = entry(account=None, card=ledger.card, value=75, installments_number=3)
    plan = InstallmentService.create(None, user=ledger.user, transaction=first)
    payload = web_payload(
        ledger,
        account='',
        card=ledger.card.pk,
        type='saida',
        value=25,
        installments_number=new_count,
        reorder_posted_dates='False',
        paid=1,
    )
    response = browser.post(reverse('update_installment', args=[plan.pk]), payload)
    assert response.status_code == 302
    assert Transaction.objects.filter(installment=plan).count() == new_count
    rows = list(Transaction.objects.filter(installment=plan).order_by('paid'))
    assert [row.paid for row in rows] == list(range(1, new_count + 1))
    assert all(row.value == 25 for row in rows)
    assert [row.payment_date for row in rows] == [
        date(2026 + (11 + index) // 12, (11 + index) % 12 + 1, 10) for index in range(new_count)
    ]


def test_installment_advance_form_shows_validation_errors(browser, ledger, entry):
    first = entry(account=None, card=ledger.card, value=75, installments_number=3)
    plan = InstallmentService.create(None, user=ledger.user, transaction=first)
    route = reverse('advance_installments', args=[plan.pk])
    assert browser.get(route).status_code == 200
    assert browser.post(route, {'quantity': 'invalid', 'initial_date': 'invalid'}).status_code == 200


def test_installment_advancement_moves_only_the_requested_count_to_the_next_invoice(browser, ledger, entry):
    first = entry(account=None, card=ledger.card, value=75, installments_number=3)
    plan = InstallmentService.create(None, user=ledger.user, transaction=first)
    response = browser.post(
        reverse('advance_installments', args=[plan.pk]), {'quantity': 2, 'initial_date': '2026-11-05'}
    )
    assert response.status_code == 302
    rows = list(Transaction.objects.filter(installment=plan).order_by('paid'))
    assert [row.payment_date for row in rows] == [date(2026, 12, 10), date(2026, 12, 10), date(2027, 1, 10)]
    assert all(row.value == 25 for row in rows)


def test_installment_advancement_rolls_back_all_dates_if_a_write_fails(browser, ledger, entry, mocker):
    from statement.services.core.transaction import TransactionService

    first = entry(account=None, card=ledger.card, value=75, installments_number=3)
    plan = InstallmentService.create(None, user=ledger.user, transaction=first)
    before = list(Transaction.objects.filter(installment=plan).order_by('pk').values_list('payment_date', flat=True))
    original_patch = TransactionService.patch
    calls = 0

    def failing_patch(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('write failed')
        return original_patch(*args, **kwargs)

    mocker.patch.object(TransactionService, 'patch', side_effect=failing_patch)
    with pytest.raises(RuntimeError, match='write failed'):
        browser.post(reverse('advance_installments', args=[plan.pk]), {'quantity': 2, 'initial_date': '2026-11-05'})
    assert (
        list(Transaction.objects.filter(installment=plan).order_by('pk').values_list('payment_date', flat=True))
        == before
    )
