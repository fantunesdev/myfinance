import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from login.password_reset import process_delivery
from login.account_email import process_account_email


class Command(BaseCommand):
    help = 'Processa a fila de recuperação sem enviar e-mails durante a requisição web.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Processa no máximo um item e encerra.')

    def handle(self, *args, **options):
        try:
            while True:
                close_old_connections()
                processed = process_delivery()
                processed = process_account_email() or processed
                if options['once']:
                    return
                if not processed:
                    time.sleep(2)
        except KeyboardInterrupt:
            return
