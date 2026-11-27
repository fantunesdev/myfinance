import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from statement.models import Bank, Device, Flag, Loan, LoanEntry, Notification, NotificationTitle


@pytest.mark.parametrize(
    'route',
    [
        'create_bank',
        'create_flag',
        'create_account',
        'create_card',
        'create_category',
        'create_subcategory',
        'create_csv_import_config',
        'create_notification',
        'create_device',
        'create_loan',
        'create_loan_entry',
        'setup_settings',
        'edit_app_config',
        'get_all_notification',
        'get_all_device',
        'user_notification_titles',
        'update_profile',
        'update_configs',
        'change_password',
        'update_next_month_view',
        'update_fuel_tracking',
        'show_dashboard',
        'import_transactions',
    ],
)
def test_standard_pages_render_forms_and_user_context(authenticated_web, route):
    response = authenticated_web.client.get(reverse(route))
    assert response.status_code == 200
    assert response.content


@pytest.mark.parametrize('route, model', [('bank', Bank), ('flag', Flag)])
def test_reference_data_create_edit_delete_flow(authenticated_web, route, model):
    client = authenticated_web.client
    response = client.post(reverse(f'create_{route}'), {'description': 'Original'})
    assert response.status_code == 302
    record = model.objects.get(description='Original')
    assert client.get(reverse(f'update_{route}', args=[record.pk])).status_code == 200
    response = client.post(reverse(f'update_{route}', args=[record.pk]), {'description': 'Updated'})
    assert response.status_code == 302
    record.refresh_from_db()
    assert record.description == 'Updated'
    assert client.get(reverse(f'delete_{route}', args=[record.pk])).status_code == 200
    assert client.post(reverse(f'delete_{route}', args=[record.pk])).status_code == 302
    assert not model.objects.filter(pk=record.pk).exists()


def test_invalid_reference_data_shows_form_errors(authenticated_web):
    response = authenticated_web.client.post(reverse('create_bank'), {'description': ''})
    assert response.status_code == 200
    assert 'description' in response.context['form'].errors
    assert not Bank.objects.exists()


@pytest.mark.parametrize('operation', ['create', 'update', 'delete'])
def test_domain_validation_failure_preserves_records_and_shows_error(authenticated_web, mocker, operation):
    record = Bank.objects.create(description='Original')
    mocker.patch(
        f'statement.views.core.bank.BankService.{operation}', side_effect=ValidationError('Operação rejeitada')
    )
    route = reverse(f'{operation}_bank', args=[] if operation == 'create' else [record.pk])
    response = authenticated_web.client.post(route, {'description': 'Updated'})
    assert response.status_code == 200
    assert 'Operação rejeitada' in response.content.decode()
    record.refresh_from_db()
    assert record.description == 'Original'


def test_device_lifecycle_stays_scoped_to_the_authenticated_user(authenticated_web):
    client = authenticated_web.client
    response = client.post(reverse('create_device'), {'name': 'Telefone'})
    assert response.status_code == 302
    device = Device.objects.get()
    assert device.user == authenticated_web.user and device.token
    assert client.get(reverse('detail_device', args=[device.pk])).status_code == 200
    assert client.post(reverse('update_device', args=[device.pk]), {'name': 'Tablet'}).status_code == 302
    device.refresh_from_db()
    assert device.name == 'Tablet'
    assert client.post(reverse('delete_device', args=[device.pk])).status_code == 302
    assert not Device.objects.exists()


def test_notification_list_and_detail_include_only_the_current_users_records(authenticated_web):
    item = Notification.objects.create(user=authenticated_web.user, app='test.app', title='Compra', message='Mensagem')
    response = authenticated_web.client.get(reverse('get_all_notification'))
    assert response.status_code == 200
    assert item in response.context['instances']
    assert authenticated_web.client.get(reverse('detail_notification', args=[item.pk])).status_code == 200
    authenticated_web.user.is_staff = False
    authenticated_web.user.save()
    response = authenticated_web.client.get(reverse('get_all_notification'))
    assert 'user' not in response.context['fields']


@pytest.mark.parametrize('route', ['setup_settings', 'edit_app_config', 'edit_notification_titles'])
def test_global_settings_reject_nonstaff_users(authenticated_web, route):
    authenticated_web.user.is_staff = False
    authenticated_web.user.save()
    assert authenticated_web.client.get(reverse(route)).status_code == 403


def test_staff_can_toggle_classifier_and_notification_preferences(authenticated_web):
    client = authenticated_web.client
    assert client.post(reverse('edit_app_config'), {'enable_transaction_classifier': 'on'}).status_code == 302
    title = NotificationTitle.objects.create(title='Compra')
    response = client.post(reverse('edit_notification_titles'), {'enabled_ids': [title.pk]})
    assert response.status_code == 302
    assert authenticated_web.user.notification_title_preferences.get(title=title).enabled
    assert client.get(reverse('edit_notification_titles')).status_code == 302


@pytest.mark.parametrize('status', ['ativos', 'inativos'])
def test_loan_lists_are_scoped_and_include_balances(authenticated_web, status):
    loan = Loan.objects.create(
        user=authenticated_web.user, description='Empréstimo', status='active' if status == 'ativos' else 'inactive'
    )
    LoanEntry.objects.create(
        user=authenticated_web.user, loan=loan, date='2026-11-05', description='Recebido', value=100
    )
    response = authenticated_web.client.get(reverse('get_loans_by_status', args=[status]))
    assert response.status_code == 200
    assert next(iter(response.context['instances'])).balance == 100
    detail = authenticated_web.client.get(reverse('detail_loan', args=[loan.pk]))
    assert detail.status_code == 200
    assert detail.context['balance'] == 100


def test_loan_entry_form_can_preselect_a_loan(authenticated_web):
    loan = Loan.objects.create(user=authenticated_web.user, description='Empréstimo')
    response = authenticated_web.client.get(reverse('create_loan_entry'), {'loan': loan.pk})
    assert response.status_code == 200
    assert str(response.context['form']['loan'].value()) == str(loan.pk)


def test_unknown_loan_status_returns_not_found(authenticated_web):
    assert authenticated_web.client.get(reverse('get_loans_by_status', args=['invalid'])).status_code == 404


@pytest.mark.parametrize(
    'service, method',
    [
        ('AppConfig', 'get_solo'),
        ('NotificationTitleService', 'ensure_titles'),
        ('NotificationService', 'get_by_filter'),
    ],
)
def test_settings_page_remains_available_when_optional_data_fails(authenticated_web, mocker, service, method):
    target = (
        'statement.views.settings_view.' + service
        if service != 'NotificationTitleService'
        else 'statement.services.core.notification_title.NotificationTitleService'
    )
    mocker.patch(f'{target}.{method}', side_effect=RuntimeError('unavailable'))
    assert authenticated_web.client.get(reverse('setup_settings')).status_code == 200
