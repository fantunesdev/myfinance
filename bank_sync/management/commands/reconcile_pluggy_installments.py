"""Repair confirmed card occurrences without creating additional expenses."""
import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from bank_sync.installment_groups import attach_installment_group
from bank_sync.models import ExternalTransaction
from bank_sync.services import payment_due_date


class Command(BaseCommand):
    help = 'Agrupa parcelas confirmadas. Simula por padrão; --source-dates também corrige os vencimentos.'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=int, required=True)
        parser.add_argument('--transactions', type=int, nargs='+', required=True)
        parser.add_argument('--source-dates', action='store_true')
        parser.add_argument('--apply', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        user = get_user_model().objects.select_for_update().get(pk=options['user'])
        sources = list(ExternalTransaction.objects.select_for_update().filter(
            account__connection__user=user, transaction_id__in=options['transactions'],
            state__in=['imported', 'linked'],
        ).select_related('transaction', 'account__card', 'account__connection'))
        if {s.transaction_id for s in sources} != set(options['transactions']):
            raise CommandError('Todos os IDs devem possuir ocorrência confirmada deste usuário.')
        def snapshot(target):
            return {'payment_date': str(target.payment_date), 'installment': target.installment_id,
                    'total': target.installments_number, 'value': str(target.value)}

        before = {s.transaction_id: snapshot(s.transaction) for s in sources}
        for source in sources:
            target = source.transaction
            if source.facts.get('payment_type') != 'INSTALLMENT':
                raise CommandError(f'A ocorrência {source.pk} não é uma parcela.')
            if options['source_dates']:
                due = payment_due_date(source)
                if not due:
                    raise CommandError(f'Sem vencimento para a ocorrência {source.pk}.')
                if target.payment_date != due:
                    target.payment_date = due
                    target.save(update_fields=['payment_date'])
            if not attach_installment_group(source, target):
                raise CommandError(f'O grupo da ocorrência {source.pk} precisa de revisão.')
        report = []
        for source in sources:
            source.transaction.refresh_from_db()
            report.append({'transaction': source.transaction_id, 'before': before[source.transaction_id],
                           'after': snapshot(source.transaction)})
        self.stdout.write(json.dumps({'applied': options['apply'], 'transactions': report}, ensure_ascii=False))
        if not options['apply']:
            transaction.set_rollback(True)
