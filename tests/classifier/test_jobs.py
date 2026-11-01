import uuid
from unittest.mock import patch

import pytest
from django.urls import include, path
from requests import Response as HTTPResponse
from requests.exceptions import HTTPError, Timeout
from rest_framework.routers import DefaultRouter
from rest_framework.test import APIClient

from api.views.transaction_classifier import TransactionClassifierView
from login.models import User
from statement.models import CategorizationFeedback, ClassifierJob
from statement.services.core import classifier_jobs as jobs

router = DefaultRouter()
router.register('transaction-classifier', TransactionClassifierView, basename='classifier')
urlpatterns = [path('api/', include(router.urls))]
pytestmark = pytest.mark.django_db


@pytest.fixture
def context(settings):
    settings.ROOT_URLCONF = __name__
    user = User.objects.create(username='classifier', email='classifier@test.invalid')
    client = APIClient()
    client.force_authenticate(user)
    feedback = CategorizationFeedback.objects.create(
        user=user,
        description='original',
        corrected_description='correção',
    )
    return user, client, feedback


def event(job, status='running', revision=2, **extra):
    return {
        'id': str(job.pk),
        'predictor': job.predictor,
        'operation': job.operation,
        'status': status,
        'revision': revision,
        'stage': 'training',
        **extra,
    }


def missing():
    response = HTTPResponse()
    response.status_code = 404
    return HTTPError(response=response)


def test_click_returns_202_and_timeout_keeps_job_pending(context):
    user, client, feedback = context
    key = str(uuid.uuid4())
    with patch.object(jobs, 'TransactionClassifierClient') as factory:
        factory.return_value.job_status.side_effect = missing()
        factory.return_value.start_job.side_effect = Timeout('lost acceptance')
        response = client.post('/api/transaction-classifier/description/feedback/', HTTP_IDEMPOTENCY_KEY=key)
    assert response.status_code == 202
    assert response.data['job']['id'] == key
    assert response.data['job']['status'] == 'submitting'
    assert 'secret' not in response.data['job']
    feedback.refresh_from_db()
    assert not feedback.description_training
    assert ClassifierJob.objects.get(pk=key).feedback_ids == [feedback.pk]


def test_repeated_id_or_click_returns_existing_active_job(context):
    user, _, _ = context
    job = jobs.create_job(user, 'description', 'feedback')
    assert jobs.create_job(user, 'description', 'feedback', job.pk).pk == job.pk
    assert jobs.create_job(user, 'description', 'train').pk == job.pk
    assert ClassifierJob.objects.count() == 1
    other = User.objects.create(username='other', email='other@test.invalid')
    with pytest.raises(ValueError):
        jobs.create_job(other, 'description', 'train', job.pk)


def test_completion_marks_only_applied_feedbacks_in_snapshot(context):
    user, _, first = context
    skipped = CategorizationFeedback.objects.create(user=user, description='same', corrected_description='same')
    job = jobs.create_job(user, 'description', 'feedback')
    added = CategorizationFeedback.objects.create(user=user, description='new', corrected_description='changed')
    jobs.apply_update(
        job.pk,
        event(
            job,
            'succeeded',
            result={
                'success': True,
                'processed_feedback_ids': [first.pk, added.pk],
                'message': 'OK',
            },
        ),
    )
    for feedback in (first, skipped, added):
        feedback.refresh_from_db()
    assert first.description_training
    assert not skipped.description_training
    assert not added.description_training


def test_full_train_resets_feedback_only_after_confirmed_success(context):
    user, _, feedback = context
    feedback.subcategory_training = True
    feedback.save()
    job = jobs.create_job(user, 'subcategory', 'train')
    feedback.refresh_from_db()
    assert feedback.subcategory_training
    jobs.apply_update(job.pk, event(job, 'failed', message='error'))
    feedback.refresh_from_db()
    assert feedback.subcategory_training
    job = jobs.create_job(user, 'subcategory', 'train')
    jobs.apply_update(job.pk, event(job, 'succeeded', result={'success': True, 'processed_feedback_ids': []}))
    feedback.refresh_from_db()
    assert not feedback.subcategory_training


def test_false_success_is_rejected_without_marking_feedback(context):
    user, _, feedback = context
    job = jobs.create_job(user, 'description', 'feedback')
    with pytest.raises(ValueError, match='confirmação'):
        jobs.apply_update(job.pk, event(job, 'succeeded', result={'success': False}))
    job.refresh_from_db()
    feedback.refresh_from_db()
    assert job.status == 'submitting'
    assert not feedback.description_training


def test_updates_are_monotonic_and_terminal_state_is_stable(context):
    user, _, _ = context
    job = jobs.create_job(user, 'description', 'feedback')
    jobs.apply_update(job.pk, event(job, revision=10, completed=5))
    jobs.apply_update(job.pk, event(job, revision=5, completed=1))
    job.refresh_from_db()
    assert job.progress['completed'] == 5
    jobs.apply_update(job.pk, event(job, 'failed', 11, message='confirmed'))
    jobs.apply_update(job.pk, event(job, revision=12))
    job.refresh_from_db()
    assert job.status == 'failed'


def test_callback_requires_per_job_secret_and_valid_identity(context):
    user, _, _ = context
    job = jobs.create_job(user, 'description', 'feedback')
    anonymous = APIClient()
    url = f'/api/transaction-classifier/jobs/{job.pk}/events/'
    assert anonymous.post(url, event(job), format='json').status_code == 403
    bad = event(job)
    bad['predictor'] = 'subcategory'
    assert anonymous.post(url, bad, format='json', HTTP_X_CLASSIFIER_SECRET=job.secret).status_code == 400
    assert anonymous.post(url, event(job), format='json', HTTP_X_CLASSIFIER_SECRET=job.secret).status_code == 200


def test_job_queries_are_scoped_to_owner(context):
    user, client, _ = context
    other = User.objects.create(username='other', email='other@test.invalid')
    job = jobs.create_job(other, 'description', 'train')
    assert client.get(f'/api/transaction-classifier/jobs/{job.pk}/').status_code == 404
    assert client.get('/api/transaction-classifier/jobs/').data == {'jobs': []}
    assert APIClient().get('/api/transaction-classifier/jobs/').status_code in (401, 403)


def test_recovery_pulls_completion_after_callback_was_lost(context):
    user, client, feedback = context
    job = jobs.create_job(user, 'description', 'feedback')
    completed = event(job, 'succeeded', result={'success': True, 'processed_feedback_ids': [feedback.pk]})
    with patch.object(jobs, 'TransactionClassifierClient') as factory:
        factory.return_value.job_status.return_value = completed
        response = client.get('/api/transaction-classifier/jobs/')
        factory.return_value.start_job.assert_not_called()
    assert response.data['jobs'][0]['status'] == 'succeeded'
    feedback.refresh_from_db()
    assert feedback.description_training


def test_delete_is_blocked_during_active_training(context):
    user, client, feedback = context
    jobs.create_job(user, 'description', 'feedback')
    assert client.post('/api/transaction-classifier/delete/').status_code == 409
    assert CategorizationFeedback.objects.filter(pk=feedback.pk).exists()


def test_websocket_outage_does_not_change_confirmed_result(context, django_capture_on_commit_callbacks):
    user, _, feedback = context
    job = jobs.create_job(user, 'description', 'feedback')
    with patch.object(jobs, 'get_channel_layer', side_effect=RuntimeError('offline')):
        with django_capture_on_commit_callbacks(execute=True):
            jobs.apply_update(
                job.pk, event(job, 'succeeded', result={'success': True, 'processed_feedback_ids': [feedback.pk]})
            )
    job.refresh_from_db()
    assert job.status == 'succeeded'


def test_scoped_inputs_need_task_secret_and_cannot_read_unrelated_resources(context):
    from statement.models import Category

    user, _, _ = context
    Category.objects.create(description='Alimentação', type='saida')
    job = jobs.create_job(user, 'subcategory', 'feedback')
    client = APIClient()
    url = f'/api/transaction-classifier/jobs/{job.pk}/inputs/'
    assert client.get(url + 'categories/').status_code == 403
    headers = {'HTTP_X_CLASSIFIER_SECRET': job.secret}
    response = client.get(url + 'categories/', **headers)
    assert response.status_code == 200
    assert response.data[0]['description'] == 'Alimentação'
    assert set(response.data[0]) == {'id', 'description'}
    assert client.get(url + 'transactions/', **headers).status_code == 403
    assert client.get(url + 'users/', **headers).status_code == 404
    jobs.apply_update(job.pk, event(job, 'failed'))
    assert client.get(url + 'categories/', **headers).status_code == 410


def test_training_inputs_expose_only_owners_transaction_fields(context):
    from datetime import date
    from statement.models import Category, Currency, Subcategory, Transaction

    user, _, _ = context
    other = User.objects.create(username='input-other', email='input-other@test.invalid')
    category = Category.objects.create(description='Alimentação', type='saida')
    subcategory = Subcategory.objects.create(description='Mercado', category=category)
    currency, _ = Currency.objects.get_or_create(id='BRL', defaults={'description': 'Real', 'symbol': 'R$'})
    for owner, description in ((user, 'own'), (other, 'private')):
        Transaction.objects.create(
            user=owner,
            description=description,
            category=category,
            subcategory=subcategory,
            currency=currency,
            value=10,
            type='saida',
            posted_date=date(2026, 11, 1),
            payment_date=date(2026, 11, 1),
        )
    job = jobs.create_job(user, 'subcategory', 'train')
    response = APIClient().get(
        f'/api/transaction-classifier/jobs/{job.pk}/inputs/transactions/', HTTP_X_CLASSIFIER_SECRET=job.secret
    )
    assert response.status_code == 200
    assert response.data == [{'description': 'own', 'category': category.pk, 'subcategory': subcategory.pk}]
