from types import SimpleNamespace

import pytest
import requests

from clients.pluggy.reader import PluggyReader, ProbeError


def response(payload=None, status=200, headers=None):
    return SimpleNamespace(status_code=status, headers=headers or {}, json=lambda: payload)


def reader(mocker, *responses):
    session = mocker.Mock()
    session.request.side_effect = responses
    return PluggyReader('disposable-client', 'disposable-secret', session=session, sleep=mocker.Mock())


def test_transport_retries_network_failures_only_three_times(mocker):
    client = reader(mocker, requests.Timeout(), requests.Timeout(), requests.Timeout())
    with pytest.raises(ProbeError, match='rede/timeout'):
        client.request('/accounts')
    assert client.session.request.call_count == 3
    assert [call.args[0] for call in client.sleep.call_args_list] == [1, 2]


def test_invalid_retry_after_uses_bounded_exponential_backoff(mocker):
    client = reader(mocker, response(status=429, headers={'Retry-After': 'not-a-number'}), response({'results': []}))
    assert client.request('/accounts') == {'results': []}
    client.sleep.assert_called_once_with(1)


def test_expired_api_key_is_refreshed_once_before_retrying(mocker):
    client = reader(mocker, response(status=401), response({'apiKey': 'renewed'}), response({'results': []}))
    assert client.request('/accounts') == {'results': []}
    assert client.api_key == 'renewed'
    assert client.session.request.call_count == 3


@pytest.mark.parametrize('payload', [[], None, 'text'])
def test_transport_rejects_unexpected_response_shapes(mocker, payload):
    with pytest.raises(ProbeError, match='Formato'):
        reader(mocker, response(payload)).request('/accounts')


def test_transport_rejects_malformed_json(mocker):
    invalid = mocker.Mock(status_code=200)
    invalid.json.side_effect = ValueError('invalid json')
    with pytest.raises(ProbeError, match='JSON'):
        reader(mocker, invalid).request('/accounts')


@pytest.mark.parametrize('payload', [{'results': 'invalid'}, {'results': [None]}, {'results': [{}]}])
def test_numbered_pagination_rejects_missing_or_invalid_rows(mocker, payload):
    client = reader(mocker, response({'page': 1, 'total': 1, 'totalPages': 1, **payload}))
    with pytest.raises(ProbeError):
        client.numbered('/accounts', {})


def test_numbered_pagination_rejects_changed_totals(mocker):
    client = reader(
        mocker,
        response({'page': 1, 'total': 2, 'totalPages': 2, 'results': [{'id': 'a'}]}),
        response({'page': 2, 'total': 3, 'totalPages': 2, 'results': [{'id': 'b'}]}),
    )
    with pytest.raises(ProbeError, match='mudou'):
        client.numbered('/accounts', {})


def test_numbered_pagination_rejects_an_empty_intermediate_page(mocker):
    client = reader(mocker, response({'page': 1, 'total': 2, 'totalPages': 2, 'results': []}))
    with pytest.raises(ProbeError, match='vazia'):
        client.numbered('/accounts', {})


def test_numbered_pagination_has_a_finite_upper_bound(mocker):
    client = PluggyReader('client', 'secret')

    def page(path, params):
        n = params['page']
        return {'page': n, 'total': 10001, 'totalPages': 10001, 'results': [{'id': str(n)}]}

    mocker.patch.object(client, 'request', side_effect=page)
    with pytest.raises(ProbeError, match='Limite'):
        client.numbered('/accounts', {})
    assert client.pages['/accounts'] == 10000


def test_cursor_pagination_has_a_finite_upper_bound(mocker):
    client = PluggyReader('client', 'secret')
    calls = 0

    def page(path, params):
        nonlocal calls
        calls += 1
        return {'results': [{'id': str(calls), 'accountId': 'account'}], 'next': f'?after={calls}'}

    mocker.patch.object(client, 'request', side_effect=page)
    with pytest.raises(ProbeError, match='Limite'):
        client.transactions('account')
    assert calls == 10000


@pytest.mark.parametrize('value', ['invalid', None])
def test_only_valid_uuid_resource_identifiers_are_accepted(value):
    assert not PluggyReader._is_uuid(value)


def test_authentication_without_an_api_key_is_rejected(mocker):
    client = reader(mocker, response({'apiKey': ''}))
    with pytest.raises(ProbeError, match='chave'):
        client.authenticate()


@pytest.mark.parametrize('total, pages', [(-1, 1), (1, -1), ('1', 1), (1, True)])
def test_numbered_pagination_requires_valid_integer_metadata(mocker, total, pages):
    client = reader(mocker, response({'page': 1, 'total': total, 'totalPages': pages, 'results': []}))
    with pytest.raises(ProbeError, match='Metadados'):
        client.numbered('/accounts', {})
