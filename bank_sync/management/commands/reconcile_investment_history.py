import json
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from bank_sync.models import BankConnection
from bank_sync.auto_reconciliation import auto_reconcile


class Command(BaseCommand):
    help = 'Prevê vínculos seguros nos dados já coletados; --apply grava somente os vínculos.'

    def add_arguments(self, parser):
        parser.add_argument('--connection', type=int, required=True)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        try:
            connection = BankConnection.objects.select_related('user').get(pk=options['connection'])
            result = auto_reconcile(connection, dry_run=not options['apply'])
        except (BankConnection.DoesNotExist, ValidationError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(json.dumps({'applied': options['apply'], **result}))
