import json
from datetime import date
from types import SimpleNamespace

import pytest
import requests

from clients.transaction_classifier.base_microservice import BaseMicroserviceClient
from clients.transaction_classifier.description_predictor import DescriptionPredictorClient
from clients.transaction_classifier.subcategory_predictor import SubcategoryPredictorClient
from clients.transaction_classifier.transaction_classifier import TransactionClassifierClient


@pytest.fixture
def transport(mocker):
    mocker.patch(
        'clients.transaction_classifier.base_microservice.JWTUtils.generate_access_token_for_user',
        return_value='test-token',
    )
    response = mocker.Mock()
    response.json.return_value = {'result': 'ok'}
    send = mocker.Mock(return_value=response)
    mocker.patch.object(BaseMicroserviceClient, 'request_method', {'get': send, 'post': send})
    mocker.patch.object(BaseMicroserviceClient, 'BASE_URL', 'http://classifier.invalid')
    mocker.patch.object(BaseMicroserviceClient, 'PORT', '8080')
    return SimpleNamespace(send=send, response=response)


@pytest.mark.parametrize('method', ['get', 'post'])
def test_transport_authenticates_and_returns_json(transport, method):
    client = BaseMicroserviceClient(object())
    assert client._send_requisition('predict', method, {'description': 'Mercado'}, timeout=(3, 8)) == {'result': 'ok'}
    transport.send.assert_called_once_with(
        'http://classifier.invalid:8080/predict',
        headers={'Authorization': 'Bearer test-token'},
        json={'description': 'Mercado'},
        timeout=(3, 8),
    )
    transport.response.raise_for_status.assert_called_once()


def test_transport_propagates_http_errors_before_reading_json(transport):
    transport.response.raise_for_status.side_effect = requests.HTTPError('unavailable')
    with pytest.raises(requests.HTTPError):
        BaseMicroserviceClient(object())._send_requisition('predict', 'post')
    transport.response.json.assert_not_called()


@pytest.mark.parametrize(
    'client_type, endpoint',
    [(DescriptionPredictorClient, 'description_predictor'), (SubcategoryPredictorClient, 'subcategories_predictor')],
)
def test_predictor_training_batch_and_feedback_contracts(transport, client_type, endpoint):
    client = client_type(object())
    assert client.train() == {'result': 'ok'}
    assert transport.send.call_args.args[0].endswith(f'/{endpoint}/train')
    rows = [{'description': 'Mercado', 'category': 'Alimentação'}]
    client.predict_batch(rows)
    assert json.loads(transport.send.call_args.kwargs['json']) == rows
    assert transport.send.call_args.args[0].endswith(f'/{endpoint}/predict-batch')
    client.retrain_from_feedback([])
    assert transport.send.call_args.args[0].endswith(f'/{endpoint}/feedback')
    assert transport.send.call_args.kwargs['json'] == []


def test_classifier_combines_both_predictors_and_preserves_context(transport):
    transport.response.json.side_effect = [{'category_id': 1, 'subcategory_id': 2}, {'description': 'Mercado'}]
    client = TransactionClassifierClient(object())
    assert client.predict('LOJA ORIGINAL', source_category='SUPERMERCADO', source_type='csv') == {
        'category_id': 1,
        'subcategory_id': 2,
        'description': 'Mercado',
    }
    requests_sent = transport.send.call_args_list
    assert requests_sent[0].kwargs['json']['source_category'] == 'SUPERMERCADO'
    assert requests_sent[1].kwargs['json']['source_type'] == 'csv'


def test_classifier_status_parses_dates_but_retains_missing_dates(transport):
    transport.response.json.return_value = {
        'data': [{'name': 'description', 'date': '2026-11-05'}, {'name': 'subcategory', 'date': None}]
    }
    response = TransactionClassifierClient(object()).status()
    assert response['data'][0].date == date(2026, 11, 5)
    assert response['data'][1].date is None


def test_classifier_jobs_use_bounded_timeouts(transport):
    client = TransactionClassifierClient(object())
    job = SimpleNamespace(
        pk='job-id', predictor='description', operation='train', feedbacks=[], secret='callback-secret'
    )
    client.start_job(job)
    assert transport.send.call_args.kwargs['timeout'] == (3, 8)
    assert transport.send.call_args.kwargs['json']['callback_secret'] == 'callback-secret'
    client.job_status(job.pk)
    assert transport.send.call_args.args[0].endswith('/jobs/job-id')
    assert transport.send.call_args.kwargs['timeout'] == (2, 3)
