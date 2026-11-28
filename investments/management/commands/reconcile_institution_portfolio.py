import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand, CommandError

from investments.services.institution_reconciliation import apply_plan


class Command(BaseCommand):
    help = 'Confere produtos e avaliações independentes; simula por padrão, sem criar fluxos financeiros.'

    def add_arguments(self, parser):
        parser.add_argument('plan', type=Path)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        try:
            plan = json.loads(options['plan'].read_text())
            user = get_user_model().objects.get(pk=plan['user_id'])
            report = apply_plan(user, plan, dry_run=not options['apply'])
        except (ValidationError, ValueError, KeyError, ObjectDoesNotExist) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
