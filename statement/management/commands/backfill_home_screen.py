from django.core.management.base import BaseCommand

from statement.models import Transaction


class Command(BaseCommand):
    help = 'Backfill Transaction.home_screen according to card_number -> card -> account rules'

    def handle(self, *args, **options):
        qs = Transaction.objects.select_related('card_number__card', 'card', 'account').all()
        to_update = []
        batch = 0
        chunk = 500
        for t in qs.iterator():
            desired = t.home_screen
            if t.card_number is not None:
                desired = t.card_number.home_screen
            elif t.card is not None:
                desired = t.card.home_screen
            elif t.account is not None:
                desired = t.account.home_screen

            if t.home_screen != desired:
                t.home_screen = desired
                to_update.append(t)

            if len(to_update) >= chunk:
                Transaction.objects.bulk_update(to_update, ['home_screen'])
                batch += 1
                self.stdout.write(f'Updated batch {batch} ({len(to_update)} items)')
                to_update = []

        if to_update:
            Transaction.objects.bulk_update(to_update, ['home_screen'])
            self.stdout.write(f'Updated final batch ({len(to_update)} items)')

        self.stdout.write('Backfill complete')
