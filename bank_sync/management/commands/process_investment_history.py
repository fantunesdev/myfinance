import time
import uuid
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from bank_sync.models import InvestmentHistoryJob, BankConnection
from bank_sync.investment_events import collect
from bank_sync.auto_reconciliation import auto_reconcile
from bank_sync.event_import import import_events


class Command(BaseCommand):
    help = 'Coleta históricos, preserva vínculos e registra movimentações com evidência completa.'

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
                    with transaction.atomic():
                        job.state = 'succeeded'
                        job.save(update_fields=['state'])
                        result = auto_reconcile(job.connection, job=job, lease_token=token)
                        imported = import_events(job.connection, job=job, lease_token=token)
                        job.progress['automatic_events'] = len(result['events'])
                        job.progress['automatic_bank_entries'] = len(result['bank_entries'])
                        job.progress['imported_events'] = len(imported['applied'])
                        job.progress['adopted_events'] = len(imported['adopted'])
                        job.message = (f'{count} eventos coletados; {len(result["events"])} eventos e '
                                       f'{len(result["bank_entries"])} comprovantes vinculados; '
                                       f'{len(imported["applied"])} movimentações registradas automaticamente.')
                        job.save(update_fields=['progress', 'message'])
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
