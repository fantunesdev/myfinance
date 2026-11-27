from datetime import date
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.http import Http404
from rest_framework.test import APIRequestFactory, force_authenticate

from api.serializers.dream import DreamSerializer
from api.serializers.file_handler_serializer import FileHandlerSerializer
from api.services.default_services import get_defaults
from api.views.account import AccountView
from api.views.category import CategoryView
from api.views.next_month_view_view import NextMonthView
from api.views.subcategory import SubcategoryView
from api.views.validate_token import ValidateTokenView
from statement.models import Account, Category, Dream, Version
from statement.services.next_month_view import NextMonthViewService
from statement.utils.jwt import JWTUtils


def dispatch(view, user, action, method='get', data=None, **kwargs):
    request = getattr(APIRequestFactory(), method)('/api/', data or {}, format='json')
    force_authenticate(request, user=user)
    return view.as_view({method: action})(request, **kwargs)


def test_account_api_list_retrieve_partial_update_and_delete(ledger):
    response = dispatch(AccountView, ledger.user, 'list')
    assert [row['id'] for row in response.data] == [ledger.account.pk]
    assert dispatch(AccountView, ledger.user, 'retrieve', pk=ledger.account.pk).status_code == 200
    response = dispatch(
        AccountView, ledger.user, 'partial_update', 'patch', {'number': 'updated'}, pk=ledger.account.pk
    )
    assert response.status_code == 200
    ledger.account.refresh_from_db()
    assert ledger.account.number == 'updated'
    assert ledger.account.bank_id is not None
    ledger.card.delete()
    assert dispatch(AccountView, ledger.user, 'destroy', 'delete', pk=ledger.account.pk).status_code == 204
    assert not Account.objects.filter(pk=ledger.account.pk).exists()


@pytest.mark.parametrize('action, method', [('retrieve', 'get'), ('partial_update', 'patch'), ('destroy', 'delete')])
def test_missing_api_resource_returns_not_found(ledger, action, method):
    assert dispatch(AccountView, ledger.user, action, method, pk=999999).status_code == 404


@pytest.mark.parametrize(
    'action, method, service_method',
    [
        ('retrieve', 'get', 'get_by_id'),
        ('partial_update', 'patch', 'update'),
        ('destroy', 'delete', 'delete'),
    ],
)
def test_api_domain_validation_returns_bad_request(ledger, mocker, action, method, service_method):
    mocker.patch(f'api.views.account.AccountService.{service_method}', side_effect=ValidationError('Operação inválida'))
    response = dispatch(AccountView, ledger.user, action, method, {'number': 'new'}, pk=ledger.account.pk)
    assert response.status_code == 400
    assert response.data['detail'] == ['Operação inválida']
    assert Account.objects.filter(pk=ledger.account.pk).exists()


def test_api_create_domain_validation_returns_bad_request(ledger, mocker):
    mocker.patch('api.views.account.AccountService.create', side_effect=ValidationError('Operação inválida'))
    response = dispatch(
        AccountView, ledger.user, 'create', 'post', {'bank': ledger.account.bank_id, 'type': ledger.account.type_id}
    )
    assert response.status_code == 400
    assert Account.objects.filter(user=ledger.user).count() == 1


def test_invalid_account_update_does_not_change_original_data(ledger):
    response = dispatch(AccountView, ledger.user, 'update', 'put', {'bank': 'invalid'}, pk=ledger.account.pk)
    assert response.status_code == 400
    ledger.account.refresh_from_db()
    assert ledger.account.bank_id is not None


def test_category_actions_filter_type_and_return_subcategories(ledger):
    response = dispatch(CategoryView, ledger.user, 'get_by_type', type='saida')
    assert response.status_code == 200
    assert [row['id'] for row in response.data] == [ledger.category.pk]
    assert dispatch(CategoryView, ledger.user, 'get_by_type', type='entrada').status_code == 404
    response = dispatch(CategoryView, ledger.user, 'get_subcategories', pk=ledger.category.pk)
    assert response.status_code == 200
    assert [row['id'] for row in response.data] == [ledger.subcategory.pk]
    empty = Category.objects.create(description='Empty')
    assert dispatch(CategoryView, ledger.user, 'get_subcategories', pk=empty.pk).status_code == 404


def test_subcategory_api_list_and_retrieve(ledger):
    response = dispatch(SubcategoryView, ledger.user, 'list')
    assert response.status_code == 200
    assert [row['id'] for row in response.data] == [ledger.subcategory.pk]
    assert (
        dispatch(SubcategoryView, ledger.user, 'retrieve', pk=ledger.subcategory.pk).data['id'] == ledger.subcategory.pk
    )


def test_defaults_require_a_release_and_return_the_latest_version(ledger):
    with pytest.raises(Http404):
        get_defaults()
    Version.objects.create(version='v1', date=date(2026, 1, 1))
    Version.objects.create(version='v2', date=date(2026, 2, 1))
    assert get_defaults() == {'version': 'v2', 'year': date.today().year}


def test_next_month_api_reads_profile_and_returns_not_found_if_missing(ledger):
    request = APIRequestFactory().get('/api/next-month/')
    force_authenticate(request, user=ledger.user)
    assert NextMonthView.as_view()(request).status_code == 404
    NextMonthViewService.create(ledger.user, day=20, active=True)
    assert NextMonthView.as_view()(request).data == {'day': 20, 'active': True}


@pytest.mark.parametrize('header', [None, 'Basic invalid', 'Bearer invalid'])
def test_validate_token_rejects_missing_wrong_scheme_and_invalid_tokens(ledger, header):
    request = APIRequestFactory().get('/api/validate/', **({'HTTP_AUTHORIZATION': header} if header else {}))
    response = ValidateTokenView.as_view()(request)
    assert response.status_code == 401
    assert response.data == {'valid': False}


def test_validate_token_accepts_a_signed_access_token(ledger):
    token = JWTUtils.generate_access_token_for_user(ledger.user)
    request = APIRequestFactory().get('/api/validate/', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert ValidateTokenView.as_view()(request).data == {'valid': True}


def test_dream_serializer_reports_progress_and_remaining_value(ledger, entry):
    dream = Dream.objects.create(user=ledger.user, description='Meta', target_value=300)
    entry(dream=dream, value=100)
    data = DreamSerializer(dream).data
    assert data['current_value'] == 100
    assert data['remaining_value'] == 200
    assert data['progress_percentage'] == 33.33


@pytest.mark.parametrize('missing', ['file', 'source', 'user'])
def test_upload_serializer_rejects_missing_required_context(missing):
    request = SimpleNamespace(FILES={'file': object()}, data={'account': '1', 'card': ''}, user=object())
    if missing == 'file':
        request.FILES.clear()
    elif missing == 'source':
        request.data['account'] = ''
    else:
        request.user = None
    serializer = FileHandlerSerializer(request)
    assert not serializer.is_valid()
    assert serializer.error_message


@pytest.mark.parametrize('source', ['account', 'card'])
def test_upload_serializer_exposes_valid_upload_context(source):
    file = object()
    user = object()
    serializer = FileHandlerSerializer(
        SimpleNamespace(FILES={'file': file}, data={'account': '', 'card': '', source: '1'}, user=user)
    )
    assert serializer.is_valid()
    assert serializer.file == (file,)
    assert serializer.user is user
    assert getattr(serializer, source) == ('1',)
    assert serializer.error_message == ''
