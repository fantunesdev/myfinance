import secrets

from django.shortcuts import get_object_or_404
from requests.exceptions import RequestException
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from clients.transaction_classifier.transaction_classifier import TransactionClassifierClient
from statement.models import Category, ClassifierJob, Subcategory, Transaction
from statement.services.core import classifier_jobs as jobs


class TransactionClassifierView(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='status')
    def status(self, request):
        try:
            result = TransactionClassifierClient(request.user).status()
            return Response({'message': result['message']})
        except RequestException:
            return Response({'error': 'Classificador indisponível.'}, status=503)

    def _start(self, request, predictor, operation):
        try:
            job = jobs.create_job(request.user, predictor, operation, request.headers.get('Idempotency-Key'))
            job = jobs.reconcile(job)
            return Response({'job': jobs.public_job(job)}, status=202)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=400)

    @action(detail=False, methods=['post'], url_path='subcategory/train')
    def subcategory_train(self, request):
        return self._start(request, 'subcategory', 'train')

    @action(detail=False, methods=['post'], url_path='subcategory/feedback')
    def subcategory_feedback(self, request):
        return self._start(request, 'subcategory', 'feedback')

    @action(detail=False, methods=['post'], url_path='description/train')
    def description_train(self, request):
        return self._start(request, 'description', 'train')

    @action(detail=False, methods=['post'], url_path='description/feedback')
    def description_feedback(self, request):
        return self._start(request, 'description', 'feedback')

    @action(detail=False, methods=['get'], url_path='jobs')
    def jobs(self, request):
        result = []
        for predictor in ('subcategory', 'description'):
            job = ClassifierJob.objects.filter(user=request.user, predictor=predictor).order_by('-created_at').first()
            if job:
                result.append(jobs.public_job(jobs.reconcile(job)))
        return Response({'jobs': result})

    @action(detail=False, methods=['get'], url_path=r'jobs/(?P<job_id>[0-9a-f-]{36})')
    def job(self, request, job_id):
        job = get_object_or_404(ClassifierJob, pk=job_id, user=request.user)
        return Response({'job': jobs.public_job(jobs.reconcile(job))})

    @action(
        detail=False,
        methods=['post'],
        url_path=r'jobs/(?P<job_id>[0-9a-f-]{36})/events',
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def job_event(self, request, job_id):
        job = get_object_or_404(ClassifierJob, pk=job_id)
        if not secrets.compare_digest(request.headers.get('X-Classifier-Secret', ''), job.secret):
            return Response({'error': 'Credencial inválida.'}, status=403)
        try:
            updated = jobs.apply_update(job.pk, request.data)
        except (ValueError, TypeError, KeyError) as exc:
            return Response({'error': str(exc)}, status=400)
        return Response({'revision': updated.revision})

    @action(
        detail=False,
        methods=['get'],
        url_path=r'jobs/(?P<job_id>[0-9a-f-]{36})/inputs/(?P<resource>categories|subcategories|transactions)',
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def job_inputs(self, request, job_id, resource):
        job = get_object_or_404(ClassifierJob, pk=job_id)
        if not secrets.compare_digest(request.headers.get('X-Classifier-Secret', ''), job.secret):
            return Response({'error': 'Credencial inválida.'}, status=403)
        if job.status in jobs.TERMINAL:
            return Response({'error': 'Tarefa encerrada.'}, status=410)
        if job.predictor != 'subcategory' or (job.operation == 'feedback' and resource != 'categories'):
            return Response({'error': 'Dados fora do escopo da tarefa.'}, status=403)
        if resource == 'categories':
            data = Category.objects.order_by('pk').values('id', 'description')
        elif resource == 'subcategories':
            data = Subcategory.objects.order_by('pk').values('id', 'category', 'description')
        else:
            data = (
                Transaction.objects.filter(user_id=job.user_id)
                .order_by('posted_date', 'pk')
                .values(
                    'id', 'posted_date', 'value', 'installment',
                    'merchant_description', 'source_type', 'source_app', 'event_type', 'source_notification',
                    'description',
                    'original_description',
                    'source_category',
                    'category',
                    'subcategory',
                )
            )
        return Response(list(data))

    @action(detail=False, methods=['post'], url_path='subcategory/delete')
    def delete_subcategory_feedbacks(self, request):
        return self._delete(request, 'subcategory')

    @action(detail=False, methods=['post'], url_path='delete')
    def delete_feedbacks(self, request):
        return self._delete(request)

    def _delete(self, request, predictor=None):
        try:
            jobs.delete_feedbacks(request.user, predictor)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=409)
        return Response({'message': 'Feedbacks apagados com sucesso.'})
