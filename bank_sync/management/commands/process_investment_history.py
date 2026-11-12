import time
import uuid
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from bank_sync.models import InvestmentHistoryJob, BankConnection
from bank_sync.investment_events import collect


class Command(BaseCommand):
    help = 'Processa a fila persistida de históricos de investimentos (somente coleta).'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')

    def handle(self, *args, **options):
        while True:
            now = timezone.now()
            with transaction.atomic():
                job = InvestmentHistoryJob.objects.select_for_update().filter(state='queued').order_by('id').first()
                if job:
                    job.state = 'running'
                    job.started_at = now
                    job.lease_until = now + timedelta(minutes=10)
                    job.save()
            if job:
                token = uuid.uuid4()
                acquired = (
                    BankConnection.objects.filter(pk=job.connection_id)
                    .filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now))
                    .update(
                        lease_token=token,
                        lease_until=now + timedelta(minutes=10),
                    )
                )
                if not acquired:
                    job.state = 'queued'
                    job.message = 'Aguardando a consulta atual da conexão.'
                    job.save()
                    if options['once']:
                        return
                    time.sleep(2)
                    continue
                try:
                    count = collect(job, lease_token=token)
                    job.state = 'succeeded'
                    job.message = f'{count} eventos coletados; lançamentos dependem de conciliação.'
                except Exception:
                    job.state = 'failed'
                    job.message = 'Coleta incompleta. Nenhum lançamento financeiro foi aplicado; tente novamente.'
                finally:
                    BankConnection.objects.filter(pk=job.connection_id, lease_token=token).update(
                        lease_token=None, lease_until=None
                    )
                job.finished_at = timezone.now()
                job.save()
            if options['once']:
                return
            time.sleep(2)
