from datetime import date

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory
from django.urls import reverse

from login.models import Profile
from statement.models import AppConfig, Dream, Loan, LoanEntry, SubcategoryChartConfig
from statement.services.core.subcategory import SubcategoryService
from statement.views.core.bank import BankView


@pytest.mark.parametrize(
    'status, model_status', [('ativos', 'active'), ('pausados', 'paused'), ('cancelados', 'cancelled')]
)
def test_dream_status_pages_show_only_the_selected_status(authenticated_web, status, model_status):
    own = Dream.objects.create(user=authenticated_web.user, description='Minha meta', status=model_status)
    response = authenticated_web.client.get(reverse('get_dreams_by_status', args=[status]))
    assert response.status_code == 200
    assert list(response.context['instances']) == [own]


def test_completed_dreams_are_grouped_by_completion_year_including_missing_dates(authenticated_web):
    for completion in [date(2026, 11, 5), None]:
        Dream.objects.create(
            user=authenticated_web.user, description='Meta realizada', status='completed', completion_date=completion
        )
    response = authenticated_web.client.get(reverse('get_dreams_by_status', args=['realizados']))
    assert response.status_code == 200
    groups = response.context['completed_dream_groups']
    assert [group['title'] for group in groups] == [2026, 'Sem data de conclusão']
    assert all(group['total_spent'] == 0 for group in groups)


def test_unknown_dream_status_returns_not_found(authenticated_web):
    assert authenticated_web.client.get(reverse('get_dreams_by_status', args=['invalid'])).status_code == 404


def test_loan_entry_create_and_edit_keep_the_same_loan_and_owner(authenticated_web):
    client = authenticated_web.client
    loan = Loan.objects.create(user=authenticated_web.user, description='Empréstimo')
    data = {'loan': loan.pk, 'date': '2026-11-05', 'description': 'Pagamento', 'value': 100}
    assert client.post(reverse('create_loan_entry'), data).status_code == 302
    entry = LoanEntry.objects.get()
    assert entry.user == authenticated_web.user and entry.loan == loan
    assert client.get(reverse('update_loan_entry', args=[entry.pk])).status_code == 200
    assert client.post(reverse('update_loan_entry', args=[entry.pk]), {**data, 'value': 150}).status_code == 302
    entry.refresh_from_db()
    assert entry.value == 150


@pytest.mark.parametrize('operation', ['create', 'get_all', 'detail', 'update', 'delete'])
def test_configuration_views_enforce_staff_policy_without_url_wrappers(authenticated_web, operation):
    user = authenticated_web.user
    user.is_staff = False
    user.save()
    request = RequestFactory().get('/configuration/')
    request.user = user
    with pytest.raises(PermissionDenied):
        getattr(BankView(), operation)(
            request, **({'id': 999999} if operation in ('detail', 'update', 'delete') else {})
        )


def test_chart_preferences_are_read_and_saved_for_the_authenticated_user(authenticated_web, db):
    from statement.models import Category, Subcategory

    category = Category.objects.create(description='Categoria')
    subcategory = Subcategory.objects.create(description='Subcategoria', category=category)
    SubcategoryService.ensure_chart_configs_for_user(authenticated_web.user)
    config = SubcategoryChartConfig.objects.get(user=authenticated_web.user, subcategory=subcategory)
    route = reverse('update_subcategory_chart_config', args=[config.pk])
    client = authenticated_web.client
    response = client.get(route)
    assert response.status_code == 200
    assert 'value="Excluir"' not in response.content.decode()
    assert client.post(route, {'show_in_annual_statement': 'on'}).status_code == 302
    config.refresh_from_db()
    assert config.show_in_annual_statement
    assert not config.show_in_monthly_cashflow_donut


def test_app_configuration_uses_a_new_instance_if_initial_lookup_fails(authenticated_web, mocker):
    mocker.patch('statement.views.settings_view.AppConfig.get_solo', side_effect=RuntimeError('lookup unavailable'))
    response = authenticated_web.client.get(reverse('edit_app_config'))
    assert response.status_code == 200


def test_app_configuration_preserves_form_validation_errors(authenticated_web, mocker):
    mocker.patch.object(AppConfig, 'clean', side_effect=ValidationError('Configuração inválida'))
    response = authenticated_web.client.post(reverse('edit_app_config'), {'enable_transaction_classifier': 'on'})
    assert response.status_code == 200
    assert 'Configuração inválida' in response.context['form'].non_field_errors()


def test_financial_pages_use_the_next_month_when_the_profile_requests_it(authenticated_web):
    from dateutil.relativedelta import relativedelta

    Profile.objects.filter(user=authenticated_web.user).update(use_next_month=True, next_month_day=1)
    response = authenticated_web.client.get(reverse('create_bank'))
    expected = date.today() + relativedelta(months=1)
    assert response.context['current_month'] == expected.month
    assert response.context['current_year'] == expected.year


def test_financial_pages_fall_back_to_current_month_if_profile_lookup_fails(authenticated_web, mocker):
    mocker.patch('statement.views.base_view.NextMonthViewService.get', side_effect=RuntimeError('unavailable'))
    response = authenticated_web.client.get(reverse('create_bank'))
    assert response.status_code == 200
    assert response.context['current_month'] == date.today().month
