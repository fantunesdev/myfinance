"""Reconcile durable classifier jobs without interpreting silence as failure."""
import logging
import secrets
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from requests.exceptions import HTTPError, RequestException

from clients.transaction_classifier.transaction_classifier import TransactionClassifierClient
from login.models import User
from statement.models import CategorizationFeedback, ClassifierJob

logger = logging.getLogger('myfinance')
ACTIVE = ('submitting', 'queued', 'running')
TERMINAL = ('succeeded', 'failed', 'interrupted')


def public_job(job):
    return {
        **job.progress,
        'id': str(job.pk),
        'predictor': job.predictor,
        'operation': job.operation,
        'status': job.status,
        'revision': job.revision,
        'created_at': job.created_at.isoformat(),
    }


def create_job(user, predictor, operation, request_id=None):
    job_id = uuid.UUID(str(request_id)) if request_id else uuid.uuid4()
    # Lock the user on MySQL even when their first job does not exist yet.
    with transaction.atomic():
        User.objects.select_for_update().get(pk=user.pk)
        existing = ClassifierJob.objects.filter(pk=job_id).first()
        if existing:
            if (existing.user_id, existing.predictor, existing.operation) != (user.pk, predictor, operation):
                raise ValueError('Identificador de tarefa já utilizado.')
            return existing
        existing = ClassifierJob.objects.filter(user=user, predictor=predictor, status__in=ACTIVE).first()
        if existing:
            return existing
        feedbacks = CategorizationFeedback.objects.filter(user=user).order_by('pk')
        if operation == 'feedback':
            feedbacks = feedbacks.filter(**{f'{predictor}_training': False})
        fields = (
            ('id',)
            if predictor == 'subcategory' and operation == 'train'
            else (
                'id',
                'description',
                'corrected_description',
                'predicted_subcategory_id',
                'corrected_category_id',
                'corrected_subcategory_id',
            )
        )
        snapshot = list(feedbacks.values(*fields))
        ids = [feedback['id'] for feedback in snapshot]
        if operation == 'feedback' and not ids:
            raise ValueError('Nenhum feedback disponível para treinamento.')
        return ClassifierJob.objects.create(
            id=job_id,
            user=user,
            predictor=predictor,
            operation=operation,
            secret=secrets.token_hex(32),
            feedback_ids=ids,
            feedbacks=snapshot,
        )


def notify(job_id):
    job = ClassifierJob.objects.get(pk=job_id)
    try:
        layer = get_channel_layer()
        if layer:
            async_to_sync(layer.group_send)(
                f'user_updates_{job.user_id}',
                {'type': 'classifier_changed', 'job': public_job(job)},
            )
    except Exception:
        logger.warning('Não foi possível notificar o progresso do classificador.', exc_info=True)


def apply_update(job_id, data):
    """Apply monotonic updates and feedback bookkeeping in one transaction."""
    with transaction.atomic():
        job = ClassifierJob.objects.select_for_update().get(pk=job_id)
        if str(data.get('id')) != str(job.pk) or data.get('predictor') != job.predictor:
            raise ValueError('Atualização de tarefa inválida.')
        if data.get('operation') != job.operation or data.get('status') not in (*ACTIVE[1:], *TERMINAL):
            raise ValueError('Estado de tarefa inválido.')
        revision = int(data['revision'])
        if revision <= job.revision or job.status in TERMINAL:
            return job
        if data['status'] == 'succeeded':
            result = data.get('result') or {}
            if result.get('success') is not True:
                raise ValueError('Conclusão sem confirmação de sucesso.')
            field = f'{job.predictor}_training'
            feedbacks = CategorizationFeedback.objects.filter(user_id=job.user_id, pk__in=job.feedback_ids)
            if job.operation == 'train':
                feedbacks.update(**{field: False})
            feedbacks.filter(pk__in=result.get('processed_feedback_ids', [])).update(**{field: True})
        job.status = data['status']
        job.revision = revision
        job.progress = {
            key: data[key]
            for key in ('stage', 'completed', 'total', 'heartbeat_at', 'last_progress_at', 'message', 'result')
            if key in data
        }
        if job.status in TERMINAL:
            job.feedbacks = []
        job.save(update_fields=['status', 'revision', 'progress', 'feedbacks', 'updated_at'])
        transaction.on_commit(lambda: notify(job.pk))
        return job


def reconcile(job):
    """Resubmit the same ID after uncertain acceptance; never duplicate work."""
    if job.status in TERMINAL:
        return job
    client = TransactionClassifierClient(job.user)
    try:
        try:
            data = client.job_status(job.pk)
        except HTTPError as exc:
            if exc.response is None or exc.response.status_code != 404:
                raise
            data = client.start_job(job)
        return apply_update(job.pk, data)
    except RequestException:
        logger.info('Aguardando confirmação da tarefa %s.', job.pk)
        job.refresh_from_db()
        return job


def delete_feedbacks(user, predictor=None):
    with transaction.atomic():
        User.objects.select_for_update().get(pk=user.pk)
        if ClassifierJob.objects.filter(user=user, status__in=ACTIVE).exists():
            raise ValueError('Aguarde a conclusão do treinamento antes de apagar feedbacks.')
        feedbacks = CategorizationFeedback.objects.filter(user=user)
        if predictor:
            feedbacks = feedbacks.filter(**{f'{predictor}_training': False})
        feedbacks.delete()
