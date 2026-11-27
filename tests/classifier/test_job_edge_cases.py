import pytest
import test_jobs as scenarios
from requests import Response as HTTPResponse
from requests.exceptions import HTTPError, Timeout

from statement.models import CategorizationFeedback, ClassifierJob
from statement.services.core import classifier_jobs as jobs

pytestmark = pytest.mark.django_db
context = scenarios.context
event = scenarios.event


@pytest.mark.parametrize(
    'endpoint, predictor, operation',
    [
        ('subcategory/train', 'subcategory', 'train'),
        ('subcategory/feedback', 'subcategory', 'feedback'),
        ('description/train', 'description', 'train'),
    ],
)
def test_training_endpoints_create_scoped_jobs(context, mocker, endpoint, predictor, operation):
    user, client, _ = context
    mocker.patch.object(jobs, 'TransactionClassifierClient').return_value.job_status.side_effect = Timeout('waiting')
    assert client.post(f'/api/transaction-classifier/{endpoint}/').status_code == 202
    job = ClassifierJob.objects.get()
    assert (job.user, job.predictor, job.operation) == (user, predictor, operation)


@pytest.mark.parametrize('available', [True, False])
def test_status_endpoint_has_a_stable_unavailable_response(context, mocker, available):
    _, client, _ = context
    transport = mocker.patch('api.views.transaction_classifier.TransactionClassifierClient').return_value
    if available:
        transport.status.return_value = {'message': 'ready'}
    else:
        transport.status.side_effect = Timeout('offline')
    assert client.get('/api/transaction-classifier/status/').status_code == (200 if available else 503)


@pytest.mark.parametrize('endpoint', ['delete', 'subcategory/delete'])
def test_feedback_deletion_succeeds_without_active_work(context, endpoint):
    _, client, feedback = context
    assert client.post(f'/api/transaction-classifier/{endpoint}/').status_code == 200
    assert not CategorizationFeedback.objects.filter(pk=feedback.pk).exists()


def test_feedback_job_requires_available_feedback(context):
    _, client, feedback = context
    feedback.delete()
    assert client.post('/api/transaction-classifier/description/feedback/').status_code == 400
    assert not ClassifierJob.objects.exists()


def test_terminal_job_is_returned_without_contacting_classifier(context, mocker):
    user, client, _ = context
    job = jobs.create_job(user, 'description', 'train')
    job.status = 'succeeded'
    job.save()
    transport = mocker.patch.object(jobs, 'TransactionClassifierClient')
    response = client.get(f'/api/transaction-classifier/jobs/{job.pk}/')
    assert response.status_code == 200
    assert response.data['job']['status'] == 'succeeded'
    transport.assert_not_called()


@pytest.mark.parametrize('changes', [{'operation': 'invalid'}, {'status': 'invalid'}])
def test_job_updates_reject_invalid_state_transitions(context, changes):
    user, _, _ = context
    job = jobs.create_job(user, 'description', 'train')
    with pytest.raises(ValueError):
        jobs.apply_update(job.pk, event(job, **changes))
    job.refresh_from_db()
    assert job.status == 'submitting'


def test_job_notifications_use_private_user_group(context, mocker):
    user, _, _ = context
    job = jobs.create_job(user, 'description', 'train')
    layer = mocker.Mock(group_send=mocker.AsyncMock())
    mocker.patch.object(jobs, 'get_channel_layer', return_value=layer)
    jobs.notify(job.pk)
    assert layer.group_send.call_args.args[0] == f'user_updates_{user.pk}'


@pytest.mark.parametrize('status', [None, 503])
def test_nonmissing_http_errors_do_not_resubmit_work(context, mocker, status):
    user, _, _ = context
    job = jobs.create_job(user, 'description', 'train')
    transport = mocker.patch.object(jobs, 'TransactionClassifierClient').return_value
    response = None if status is None else HTTPResponse()
    if response is not None:
        response.status_code = status
    transport.job_status.side_effect = HTTPError(response=response)
    assert jobs.reconcile(job).pk == job.pk
    transport.start_job.assert_not_called()
