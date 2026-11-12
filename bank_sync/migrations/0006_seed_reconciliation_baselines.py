from datetime import date
from django.db import migrations


def seed(apps, schema_editor):
    Investment = apps.get_model('investments', 'Investment')
    Baseline = apps.get_model('bank_sync', 'InvestmentReconciliationBaseline')
    for inv in Investment.objects.using(schema_editor.connection.alias).filter(
        notes__contains='[inter-reconcile-20261112]'
    ):
        Baseline.objects.using(schema_editor.connection.alias).get_or_create(
            investment_id=inv.pk,
            defaults={
                'date': date(2026, 11, 11),
                'evidence': 'Data-base da conciliação auditada inter-reconcile-20261112. Importações anteriores exigem substituição completa da abertura, não lançamento isolado.',
            },
        )


class Migration(migrations.Migration):
    dependencies = [('bank_sync', '0005_investmentevent_last_seen_job')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
