import os
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from dotenv import dotenv_values

from bank_sync.models import BankConnection
from bank_sync.services import sync_connection
from clients.pluggy.reader import ProbeError


class Command(BaseCommand):
    help = "Sincroniza somente dados de leitura Pluggy; não cria lançamentos financeiros."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Proprietário local explícito da conexão pessoal.")

    def handle(self, *args, **options):
        try:
            user = get_user_model().objects.get(username=options["username"], is_active=True)
            values = dotenv_values(settings.BASE_DIR / ".env.pluggy")
            item_id = UUID(os.environ.get("PLUGGY_ITEM_ID") or values.get("PLUGGY_ITEM_ID") or "")
            connection, _ = BankConnection.objects.get_or_create(item_id=item_id, defaults={"user": user})
            if connection.user_id != user.pk:
                raise CommandError("Item já pertence a outro usuário local.")
            run = sync_connection(connection)
        except (get_user_model().DoesNotExist, ValueError):
            raise CommandError("Confira --username e PLUGGY_ITEM_ID no servidor.") from None
        except (ValidationError, ProbeError) as error:
            raise CommandError(str(error)) from None
        self.stdout.write(
            self.style.SUCCESS(f"{run.transaction_count} ocorrências consultadas; nenhum lançamento criado.")
        )
