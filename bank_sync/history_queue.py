from django.db import transaction
from django.utils import timezone
from bank_sync.models import BankConnection, InvestmentHistoryJob


@transaction.atomic
def queue_history(connection):
    connection = BankConnection.objects.select_for_update().get(pk=connection.pk)
    now = timezone.now()
    InvestmentHistoryJob.objects.filter(connection=connection, state='running', lease_until__lt=now).update(
        state='failed', message='Execução interrompida; uma nova coleta pode ser solicitada.')
    job = InvestmentHistoryJob.objects.filter(connection=connection, state__in=['queued', 'running']).first()
    return job or InvestmentHistoryJob.objects.create(connection=connection)
