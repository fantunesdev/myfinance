import json
from types import SimpleNamespace

import pytest
import test_integration as scenarios
from django.test import RequestFactory

from bank_sync import views


@pytest.fixture
def card_api(authenticated_web):
    case = scenarios.PluggyIntegrationTests()
    case.setUp()
    return case


def request(user, data=None, method='post'):
    result = getattr(RequestFactory(), method)(
        '/pluggy/', data=json.dumps(data or {}) if method == 'post' else data or {}, content_type='application/json'
    )
    result.user = user
    return result


def test_card_sync_endpoint_uses_only_an_owned_connection(card_api, mocker):
    c = card_api
    sync = mocker.patch('bank_sync.views.sync_connection', return_value=SimpleNamespace(transaction_count=17))
    response = views.sync(request(c.user, {'connection_id': c.connection.pk}))
    assert response.status_code == 200
    assert json.loads(response.content) == {'count': 17}
    sync.assert_called_once_with(c.connection)


def test_card_mapping_endpoint_saves_the_explicit_card_selection(card_api):
    c = card_api
    row = c.ingest()
    response = views.map_cards(request(c.user, {'account_id': row.account_id, 'card_id': c.card.pk, 'aliases': {}}))
    assert response.status_code == 200
    row.account.refresh_from_db()
    assert row.account.card == c.card


def test_card_mapping_rejects_invalid_alias_payload(card_api):
    c = card_api
    assert views.map_cards(request(c.user, {'aliases': []})).status_code == 400


def test_card_review_endpoint_creates_one_confirmed_transaction(card_api):
    c = card_api
    row = c.mapped()
    response = views.review(
        request(c.user, {'id': row.pk, 'revision': row.revision, 'action': 'create', **c.create_data()})
    )
    assert response.status_code == 200
    assert json.loads(response.content)['transaction_id']
    row.refresh_from_db()
    assert row.state == 'imported'


def test_card_details_endpoint_returns_only_owned_candidates(card_api):
    c = card_api
    row = c.mapped()
    response = views.details(request(c.user, method='get'), row.pk)
    assert response.status_code == 200
    assert 'candidates' in json.loads(response.content)
    assert views.details(request(c.other, method='get'), row.pk).status_code == 404


@pytest.mark.parametrize('notice', ['', 'Classificador indisponível'])
def test_prediction_endpoint_exposes_safe_classifier_status(card_api, mocker, notice):
    c = card_api
    row = c.mapped()
    mocker.patch('bank_sync.views.classify', return_value=notice)
    response = views.predict(request(c.user, {'id': row.pk}))
    assert response.status_code == (400 if notice else 200)


@pytest.mark.parametrize('enabled', [True, False, 'false'])
def test_connection_preference_requires_an_actual_boolean(card_api, enabled):
    c = card_api
    response = views.preference(request(c.user, {'connection_id': c.connection.pk, 'prefer_pluggy': enabled}))
    assert response.status_code == (400 if isinstance(enabled, str) else 200)
    if not isinstance(enabled, str):
        c.connection.refresh_from_db()
        assert c.connection.prefer_pluggy is enabled


def test_card_read_endpoints_render_ledger_and_filter_owned_occurrences(card_api):
    c = card_api
    row = c.mapped()
    params = {'bill': str(row.account.bills.get().pk), 'state': 'all', 'account': row.account_id}
    assert views.state(request(c.user, params, method='get')).status_code == 200
    assert views.ledger(request(c.user, params, method='get')).status_code == 200
    assert views.bills_page(request(c.user, method='get')).status_code == 200
    params['state'] = 'ignored'
    assert views.state(request(c.user, params, method='get')).status_code == 200


def test_sync_investment_positions_requires_a_selected_or_unique_connection(card_api):
    c = card_api
    c.connection.delete()
    assert views.sync_investment_positions(request(c.user)).status_code == 400


def test_json_api_rejects_nonobject_payloads(card_api):
    raw = RequestFactory().post('/pluggy/', data='[]', content_type='application/json')
    raw.user = card_api.user
    assert views.preference(raw).status_code == 400
