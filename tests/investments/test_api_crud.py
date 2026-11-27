from datetime import date

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from api.views.investment import InvestmentView
from investments.models import Asset, Broker, Investment


def call(user, action, method='get', data=None, **kwargs):
    request = getattr(APIRequestFactory(), method)('/api/investments/', data or {}, format='json')
    force_authenticate(request, user=user)
    return InvestmentView.as_view({method: action})(request, **kwargs)


@pytest.fixture
def record(authenticated_web):
    user = authenticated_web.user
    asset = Asset.objects.create(user=user, description='CDB', asset_type='fixed_income')
    broker = Broker.objects.create(user=user, description='Banco')
    return Investment.objects.create(
        user=user, asset=asset, broker=broker, description='CDB', start_date=date(2026, 1, 1)
    )


def test_investment_api_put_and_delete_follow_the_owner_scope(record):
    data = {
        'asset': record.asset_id,
        'broker': record.broker_id,
        'description': 'Updated',
        'start_date': '2026-01-01',
        'status': 'active',
    }
    response = call(record.user, 'update', 'put', data, pk=record.pk)
    assert response.status_code == 200
    record.refresh_from_db()
    assert record.description == 'Updated'
    assert call(record.user, 'destroy', 'delete', pk=record.pk).status_code == 204
    assert not Investment.objects.filter(pk=record.pk).exists()


@pytest.mark.parametrize('action, method', [('update', 'put'), ('partial_update', 'patch'), ('destroy', 'delete')])
def test_investment_api_missing_records_return_not_found(record, action, method):
    assert call(record.user, action, method, pk=999999).status_code == 404


def test_investment_api_preserves_the_record_after_delete_validation_failure(record, mocker):
    mocker.patch('api.views.investment.InvestmentService.delete', side_effect=ValidationError('Registro protegido'))
    response = call(record.user, 'destroy', 'delete', pk=record.pk)
    assert response.status_code == 400
    assert Investment.objects.filter(pk=record.pk).exists()


def test_dashboard_returns_a_retryable_error_if_revision_keeps_changing(record, mocker):
    mocker.patch('api.views.investment.dashboard_revision', side_effect=['a', 'b', 'c', 'd'])
    mocker.patch('api.views.investment.dashboard_payload', return_value={})
    response = call(record.user, 'dashboard')
    assert response.status_code == 503
